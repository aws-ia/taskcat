import json
import logging
import random
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, NewType, Optional, Union
from uuid import UUID, uuid5

import boto3

from dataclasses_jsonschema import FieldEncoder, JsonSchemaMixin
from taskcat._cfn.template import Template
from taskcat._client_factory import Boto3Cache
from taskcat._common_utils import merge_nested_dict
from taskcat.exceptions import TaskCatException
from taskcat.local_zones import ZONES as LOCAL_ZONES

LOG = logging.getLogger(__name__)

# property descriptions

METADATA: Mapping[str, Mapping[str, Any]] = {
    "project__name": {
        "description": "Project name, used as s3 key prefix when " "uploading objects",
        "examples": ["my-project-name"],
    },
    "auth": {
        "description": "AWS authentication section",
        "examples": [
            {
                "default": "my-default-profile",
                "us-east-2": "specific-profile-for-us-east-2",
                "cn-northwest-1": "china-profile",
            }
        ],
    },
    "project__owner": {
        "description": "email address for project owner (not used at present)",
        "examples": ["Bob.Slydell@example.com"],
    },
    "regions": {"description": "List of AWS regions"},
    "artifact_regions": {
        "description": "List of AWS regions where artifacts need to be copied. This helps same region artifact bucket access to resources"
    },
    "az_ids": {
        "description": "List of Availablilty Zones ID's to exclude when generating "
        "availability zones",
    },
    "package_lambda": {
        "description": "Package Lambda functions into zips before uploading to s3, "
        "set to false to disable",
        "examples": [True, False],
    },
    "s3_regional_buckets": {
        "description": "Enable regional auto-buckets.",
        "examples": [True, False],
    },
    "lambda_zip_path": {
        "description": "Path relative to the project root to place Lambda zip " "files",
        "default": "lambda_functions/zips",
        "examples": ["functions/packages"],
    },
    "lambda_source_path": {
        "description": "Path relative to the project root containing Lambda zip "
        "files, default is 'lambda_functions/source'",
        "default": "lambda_functions/source",
        "examples": ["functions/source"],
    },
    "s3_bucket": {
        "description": "Name of S3 bucket to upload project to, if left out "
        "a bucket will be auto-generated",
        "examples": ["my-s3-bucket-name"],
    },
    "parameters": {
        "description": "Parameter key-values to pass to CloudFormation, "
        "parameters provided in global config take precedence",
    },
    "build_submodules": {
        "description": "Build Lambda zips recursively for submodules, "
        "set to false to disable",
        "default": True,
        "examples": [True, False],
    },
    "template": {
        "description": "path to template file relative to the project "
        "config file path",
        "examples": ["cloudformation_templates/"],
    },
    "tags": {
        "description": "Tags to apply to CloudFormation template",
        "examples": [{"CostCenter": "1001"}],
    },
    "enable_sig_v2": {
        "description": "Enable (deprecated) sigv2 access to auto-generated buckets",
        "default": False,
        "examples": [True, False],
    },
    "s3_object_acl": {
        "description": "ACL for uploaded s3 objects",
        "default": "private",
    },
    "shorten_stack_name": {
        "description": "Shorten stack names generated for tests, set to true to enable",
        "default": False,
        "examples": [True, False],
    },
    "role_name": {"description": "Role name to use when launching CFN Stacks."},
    "org_id": {
        "description": "Organization ID to use when launching CFN Stacks. starts with o-. It is found on Organization Settings page"
    },
    "stack_name": {"description": "Cloudformation Stack Name"},
    "stack_name_prefix": {"description": "Prefix to apply to generated CFN Stack Name"},
    "stack_name_suffix": {"description": "Suffix to apply to generated CFN Stack Name"},
    "prehooks": {"description": "hooks to execute prior to executing tests"},
    "posthooks": {"description": "hooks to execute after executing tests"},
    "type": {"description": "hook type"},
    "config": {"description": "hook configuration"},
}

# types

ParameterKey = NewType("ParameterKey", str)
ParameterValue = Union[str, int, bool, List[Union[int, str]]]
TagKey = NewType("TagKey", str)
TagValue = NewType("TagValue", str)
S3Acl = NewType("S3Acl", str)
Region = NewType("Region", str)
AlNumDash = NewType("AlNumDash", str)
AlNumDashSlash = NewType("AlNumDashSlash", str)
ProjectName = NewType("ProjectName", AlNumDashSlash)
S3BucketName = NewType("S3BucketName", AlNumDash)
TestName = NewType("TestName", AlNumDash)
AzId = NewType("AzId", str)
Templates = NewType("Templates", Dict[TestName, Template])
# regex validation


class ParameterKeyField(FieldEncoder):
    @property
    def json_schema(self):
        return {
            "type": "string",
            "pattern": r"[a-zA-Z0-9]*^$",
            "Description": "CloudFormation parameter name, can contain letters and "
            "numbers only",
            "examples": ["ExtremaFajitas", "PizzaShooters", "ShrimpPoppers"],
        }


JsonSchemaMixin.register_field_encoders({ParameterKey: ParameterKeyField()})


class RegionField(FieldEncoder):
    @property
    def json_schema(self):
        return {
            "type": "string",
            "pattern": r"^(ap|eu|us|sa|ca|cn|af|me|us-gov)-(central|south|north|east|"
            r"west|southeast|southwest|northeast|northwest)-[0-9]$",
            "description": "AWS Region name",
            "examples": ["us-east-1"],
        }


JsonSchemaMixin.register_field_encoders({Region: RegionField()})


class S3AclField(FieldEncoder):
    @property
    def json_schema(self):
        return {
            "type": "string",
            "default": "private",
            "pattern": r"^("
            r"bucket-owner-full-control|"
            r"bucket-owner-read|"
            r"authenticated-read|"
            r"aws-exec-read|"
            r"public-read-write|"
            r"public-read|"
            r"private)$",
            "description": "Must be a valid S3 ACL (private, public-read, "
            "aws-exec-read, public-read-write, authenticated-read, "
            "bucket-owner-read, bucket-owner-full-control)",
            "examples": ["bucket-owner-read", "private"],
        }


JsonSchemaMixin.register_field_encoders({S3Acl: S3AclField()})


class AlNumDashField(FieldEncoder):
    @property
    def json_schema(self):
        return {
            "type": "string",
            "pattern": r"^[a-z0-9-]*$",
            "description": "accepts lower case letters, numbers and -",
        }


JsonSchemaMixin.register_field_encoders({AlNumDash: AlNumDashField()})


class AlNumDashSlashField(FieldEncoder):
    @property
    def json_schema(self):
        return {
            "type": "string",
            "pattern": r"^[a-z0-9-/]*$",
            "description": "accepts lower case letters, numbers, -, /",
        }


JsonSchemaMixin.register_field_encoders({AlNumDashSlash: AlNumDashSlashField()})


class AzIdField(FieldEncoder):
    @property
    def json_schema(self):
        return {
            "type": "string",
            "pattern": f"({'|'.join(z for z in LOCAL_ZONES)})",
            "description": "Availability Zone ID, eg.: 'use1-az1'",
            "examples": ["usw2-laz1-az1", "use2-az2"],
        }


JsonSchemaMixin.register_field_encoders({AzId: AzIdField()})


# dataclasses
@dataclass
class RegionObj:
    name: str
    account_id: str
    partition: str
    profile: str
    taskcat_id: UUID
    _boto3_cache: Boto3Cache
    _role_name: Optional[str]

    def client(self, service: str):
        return self._boto3_cache.client(service, region=self.name, profile=self.profile)

    @property
    def session(self):
        return self._boto3_cache.session(region=self.name, profile=self.profile)

    @property
    def role_arn(self):
        if self._role_name:
            return f"arn:{self.partition}:iam::{self.account_id}:role/{self._role_name}"
        return None


@dataclass
class S3BucketObj:
    name: str
    region: str
    account_id: str
    partition: str
    s3_client: boto3.client
    sigv4: bool
    auto_generated: bool
    regional_buckets: bool
    object_acl: str
    taskcat_id: UUID
    org_id: str

    @property
    def sigv4_policy(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Test",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": f"arn:{self.partition}:s3:::{self.name}/*",
                    "Condition": {"StringEquals": {"s3:signatureversion": "AWS"}},
                }
            ],
        }
        return json.dumps(policy)

    @property
    def multi_account_policy(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Bucket access to member accounts",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": f"arn:{self.partition}:s3:::{self.name}/*",
                    "Condition": {"StringEquals": {"aws:PrincipalOrgID": self.org_id}},
                }
            ],
        }
        return json.dumps(policy)

    def create(self):
        if self._bucket_matches_existing():
            return
        kwargs = {"Bucket": self.name}
        if self.region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": self.region}

        self.s3_client.create_bucket(**kwargs)
        try:
            self.s3_client.get_waiter("bucket_exists").wait(Bucket=self.name)

            if not self.regional_buckets:
                self.s3_client.put_bucket_tagging(
                    Bucket=self.name,
                    Tagging={
                        "TagSet": [{"Key": "taskcat-id", "Value": self.taskcat_id.hex}]
                    },
                )

            if self.sigv4 is True:
                self.s3_client.put_bucket_policy(
                    Bucket=self.name, Policy=self.sigv4_policy
                )
            if self.org_id is not None:
                self.s3_client.put_bucket_policy(
                    Bucket=self.name, Policy=self.multi_account_policy
                )
        except Exception as e:  # pylint: disable=broad-except
            try:
                self.s3_client.delete_bucket(Bucket=self.name)
            except Exception as inner_e:  # pylint: disable=broad-except
                LOG.warning(f"failed to remove bucket {self.name}: {inner_e}")
            raise e

    def empty(self):
        if not self.auto_generated:
            LOG.error(f"Will not empty bucket created outside of taskcat {self.name}")
            return
        objects_to_delete = []
        pages = self.s3_client.get_paginator("list_objects_v2").paginate(
            Bucket=self.name
        )
        for page in pages:
            objects = []
            for obj in page.get("Contents", []):
                del_obj = {"Key": obj["Key"]}
                if obj.get("VersionId"):
                    del_obj["VersionId"] = obj["VersionId"]
                objects.append(del_obj)
            objects_to_delete += objects
        batched_objects = [
            objects_to_delete[i : i + 1000]
            for i in range(0, len(objects_to_delete), 1000)
        ]
        for objects in batched_objects:
            if objects:
                self.s3_client.delete_objects(
                    Bucket=self.name, Delete={"Objects": objects}
                )

    def delete(self, delete_objects=False):
        if not self.auto_generated:
            LOG.info(f"Will not delete bucket created outside of taskcat {self.name}")
            return
        if delete_objects:
            try:
                self.empty()
            except self.s3_client.exceptions.NoSuchBucket:
                LOG.info(f"Cannot delete bucket {self.name} as it does not exist")
                return
        try:
            self.s3_client.delete_bucket(Bucket=self.name)
        except self.s3_client.exceptions.NoSuchBucket:
            LOG.info(f"Cannot delete bucket {self.name} as it does not exist")

    def _bucket_matches_existing(self):
        try:
            location = self.s3_client.get_bucket_location(Bucket=self.name)[
                "LocationConstraint"
            ]
            location = location if location else "us-east-1"
        except self.s3_client.exceptions.NoSuchBucket:
            location = None
        if location != self.region and location is not None:
            raise TaskCatException(
                f"bucket {self.name} already exists, but is not in "
                f"the expected region {self.region}, expected {location}"
            )
        if location:
            if self.regional_buckets:
                return True
            tags = self.s3_client.get_bucket_tagging(Bucket=self.name)["TagSet"]
            tags = {t["Key"]: t["Value"] for t in tags}
            uid = tags.get("taskcat-id")
            uid = UUID(uid) if uid else uid
            if uid != self.taskcat_id:
                raise TaskCatException(
                    f"bucket {self.name} already exists, but does not have a matching"
                    f" uuid"
                )
            return True
        return False


class Tag:
    def __init__(self, tag_dict: dict):
        if isinstance(tag_dict, Tag):
            tag_dict = {"Key": tag_dict.key, "Value": tag_dict.value}
        self.key: str = tag_dict["Key"]
        self.value: str = tag_dict["Value"]

    def dump(self):
        tag_dict = {"Key": self.key, "Value": self.value}
        return tag_dict


@dataclass
class TestRegion(RegionObj):
    __test__ = False
    s3_bucket: S3BucketObj
    parameters: Dict[ParameterKey, ParameterValue]

    @classmethod
    def from_region_obj(cls, region: RegionObj, s3_bucket, parameters):
        return cls(s3_bucket=s3_bucket, parameters=parameters, **region.__dict__)


TestRegion.__test__ = False


@dataclass
# pylint: disable=too-many-instance-attributes
class TestObj:
    __test__ = False

    def __init__(
        self,
        template_path: Path,
        template: Template,
        project_root: Path,
        name: TestName,
        regions: List[TestRegion],
        artifact_regions: List[TestRegion],
        tags: List[Tag],
        uid: UUID,
        _project_name: str,
        _stack_name: str = "",
        _stack_name_prefix: str = "",
        _stack_name_suffix: str = "",
        _shorten_stack_name: bool = False,
    ):
        self.template_path = template_path
        self.template = template
        self.project_root = project_root
        self.name = name
        self.regions = regions
        self.artifact_regions = artifact_regions
        self.tags = tags
        self.uid = uid
        self._project_name = _project_name
        self._stack_name = _stack_name
        self._stack_name_prefix = _stack_name_prefix
        self._stack_name_suffix = _stack_name_suffix
        self._shorten_stack_name = _shorten_stack_name
        self._assert_param_combo()

    def _assert_param_combo(self):
        throw = False
        if self._stack_name_prefix and self._stack_name_suffix:
            throw = True
        if self._stack_name and (self._stack_name_prefix or self._stack_name_suffix):
            throw = True
        if throw:
            raise TaskCatException(
                "Please provide only *ONE* of stack_name, stack_name_prefix, \
                or stack_name_suffix"
            )

    @property
    def stack_name(self):
        prefix = "tCaT-"
        if self._stack_name:
            return self._stack_name
        # TODO: prefix *OR* suffix
        if self._stack_name_prefix:
            if self._shorten_stack_name:
                return "{}{}-{}".format(
                    self._stack_name_prefix, self.name, self.uid.hex[:6]
                )
            return "{}{}-{}-{}".format(
                self._stack_name_prefix, self._project_name, self.name, self.uid.hex
            )
        if self._stack_name_suffix:
            return "{}{}-{}-{}".format(
                prefix, self._project_name, self.name, self._stack_name_suffix
            )
        if self._shorten_stack_name:
            return "{}{}-{}".format(prefix, self.name, self.uid.hex[:6])
        return "{}{}-{}-{}".format(prefix, self._project_name, self.name, self.uid.hex)


TestObj.__test__ = False


@dataclass
class HookData(JsonSchemaMixin, allow_additional_props=False):  # type: ignore
    """Hook definition"""

    type: Optional[str] = field(default=None, metadata=METADATA["type"])
    config: Optional[Dict[str, Any]] = field(default=None, metadata=METADATA["config"])


@dataclass
class GeneralConfig(JsonSchemaMixin, allow_additional_props=False):  # type: ignore
    """General configuration settings."""

    parameters: Optional[Dict[ParameterKey, ParameterValue]] = field(
        default=None, metadata=METADATA["parameters"]
    )
    tags: Optional[Dict[TagKey, TagValue]] = field(
        default=None, metadata=METADATA["tags"]
    )
    auth: Optional[Dict[Region, str]] = field(default=None, metadata=METADATA["auth"])
    s3_bucket: Optional[str] = field(default=None, metadata=METADATA["s3_bucket"])
    s3_regional_buckets: Optional[bool] = field(
        default=None, metadata=METADATA["s3_regional_buckets"]
    )
    regions: Optional[List[Region]] = field(default=None, metadata=METADATA["regions"])
    artifact_regions: Optional[List[Region]] = field(
        default=None, metadata=METADATA["artifact_regions"]
    )
    prehooks: Optional[List[HookData]] = field(
        default=None, metadata=METADATA["prehooks"]
    )
    posthooks: Optional[List[HookData]] = field(
        default=None, metadata=METADATA["posthooks"]
    )


@dataclass
class TestConfig(JsonSchemaMixin, allow_additional_props=False):  # type: ignore
    """Test specific configuration section."""

    template: Optional[str] = field(default=None, metadata=METADATA["template"])
    parameters: Dict[ParameterKey, ParameterValue] = field(
        default_factory=dict, metadata=METADATA["parameters"]
    )
    regions: Optional[List[Region]] = field(default=None, metadata=METADATA["regions"])
    artifact_regions: Optional[List[Region]] = field(
        default=None, metadata=METADATA["artifact_regions"]
    )
    tags: Optional[Dict[TagKey, TagValue]] = field(
        default=None, metadata=METADATA["tags"]
    )
    auth: Optional[Dict[Region, str]] = field(default=None, metadata=METADATA["auth"])
    s3_bucket: Optional[S3BucketName] = field(
        default=None, metadata=METADATA["s3_bucket"]
    )
    s3_regional_buckets: Optional[bool] = field(
        default=None, metadata=METADATA["s3_regional_buckets"]
    )
    az_blacklist: Optional[List[AzId]] = field(
        default=None, metadata=METADATA["az_ids"]
    )
    role_name: Optional[str] = field(default=None, metadata=METADATA["role_name"])

    stack_name: Optional[str] = field(default=None, metadata=METADATA["stack_name"])
    stack_name_prefix: Optional[str] = field(
        default=None, metadata=METADATA["stack_name_prefix"]
    )
    stack_name_suffix: Optional[str] = field(
        default=None, metadata=METADATA["stack_name_suffix"]
    )
    prehooks: Optional[List[HookData]] = field(
        default=None, metadata=METADATA["prehooks"]
    )
    posthooks: Optional[List[HookData]] = field(
        default=None, metadata=METADATA["posthooks"]
    )


# pylint: disable=too-many-instance-attributes
@dataclass
class ProjectConfig(JsonSchemaMixin, allow_additional_props=False):  # type: ignore
    """Project specific configuration section"""

    name: Optional[ProjectName] = field(
        default=None, metadata=METADATA["project__name"]
    )
    auth: Optional[Dict[Region, str]] = field(default=None, metadata=METADATA["auth"])
    owner: Optional[str] = field(default=None, metadata=METADATA["project__owner"])
    regions: Optional[List[Region]] = field(default=None, metadata=METADATA["regions"])
    artifact_regions: Optional[List[Region]] = field(
        default=None, metadata=METADATA["artifact_regions"]
    )
    az_blacklist: Optional[List[AzId]] = field(
        default=None, metadata=METADATA["az_ids"]
    )
    package_lambda: Optional[bool] = field(
        default=None, metadata=METADATA["package_lambda"]
    )
    lambda_zip_path: Optional[str] = field(
        default=None, metadata=METADATA["lambda_zip_path"]
    )
    lambda_source_path: Optional[str] = field(
        default=None, metadata=METADATA["lambda_source_path"]
    )
    s3_bucket: Optional[S3BucketName] = field(
        default=None, metadata=METADATA["s3_bucket"]
    )
    s3_regional_buckets: Optional[bool] = field(
        default=None, metadata=METADATA["s3_regional_buckets"]
    )
    parameters: Optional[Dict[ParameterKey, ParameterValue]] = field(
        default=None, metadata=METADATA["parameters"]
    )
    build_submodules: Optional[bool] = field(
        default=None, metadata=METADATA["build_submodules"]
    )
    template: Optional[str] = field(default=None, metadata=METADATA["template"])
    tags: Optional[Dict[TagKey, TagValue]] = field(
        default=None, metadata=METADATA["tags"]
    )
    s3_enable_sig_v2: Optional[bool] = field(
        default=None, metadata=METADATA["enable_sig_v2"]
    )
    s3_object_acl: Optional[S3Acl] = field(
        default=None, metadata=METADATA["s3_object_acl"]
    )
    shorten_stack_name: Optional[bool] = field(
        default=None, metadata=METADATA["shorten_stack_name"]
    )
    role_name: Optional[str] = field(default=None, metadata=METADATA["role_name"])

    org_id: Optional[str] = field(default=None, metadata=METADATA["org_id"])

    prehooks: Optional[List[HookData]] = field(
        default=None, metadata=METADATA["prehooks"]
    )
    posthooks: Optional[List[HookData]] = field(
        default=None, metadata=METADATA["posthooks"]
    )


PROPAGATE_KEYS = ["tags", "parameters", "auth"]
PROPOGATE_ITEMS = [
    "regions",
    "s3_bucket",
    "template",
    "az_blacklist",
    "s3_regional_buckets",
    "prehooks",
    "posthooks",
]


def generate_regional_bucket_name(region_obj: RegionObj, prefix: str = "tcat"):
    if len(prefix) > 8 or len(prefix) < 1:  # pylint: disable=len-as-condition
        raise TaskCatException("prefix must be between 1 and 8 characters long")
    hashed_account_id = uuid5(
        name=str(region_obj.account_id), namespace=UUID(int=0)
    ).hex
    return f"{prefix}-{hashed_account_id}-{region_obj.name}"


def generate_bucket_name(project: str, prefix: str = "tcat"):
    if len(prefix) > 8 or len(prefix) < 1:  # pylint: disable=len-as-condition
        raise TaskCatException("prefix must be between 1 and 8 characters long")
    alnum = string.ascii_lowercase + string.digits
    suffix = "".join(random.choice(alnum) for i in range(8))  # nosec: B311
    mid = f"-{project}-"
    avail_len = 63 - len(mid)
    mid = mid[:avail_len]
    return f"{prefix}{mid}{suffix}"


# pylint raises false positive due to json-dataclass
# pylint: disable=no-member
@dataclass
class BaseConfig(JsonSchemaMixin, allow_additional_props=False):  # type: ignore
    """Taskcat configuration file"""

    general: GeneralConfig = field(default_factory=GeneralConfig)
    project: ProjectConfig = field(default_factory=ProjectConfig)
    tests: Dict[TestName, TestConfig] = field(default_factory=dict)

    # pylint doesn't like instance variables being added in post_init
    # pylint: disable=attribute-defined-outside-init
    def __post_init__(self):
        self._source: Dict[str, Any] = {}
        self._propogate()
        self.set_source("UNKNOWN")
        self._propogate_source()

    @staticmethod
    def _merge(source, dest):
        for section_key, section_value in source.items():
            if section_key in PROPAGATE_KEYS + PROPOGATE_ITEMS:
                if section_key not in dest:
                    dest[section_key] = section_value
                    continue
                if section_key in PROPAGATE_KEYS:
                    for key, value in section_value.items():
                        dest[section_key][key] = value
        return dest

    def _propogate(self):
        project_dict = self._merge(self.general.to_dict(), self.project.to_dict())
        self.project = ProjectConfig.from_dict(project_dict)
        for test_key, test in self.tests.items():
            test_dict = self._merge(self.project.to_dict(), test.to_dict())
            self.tests[test_key] = TestConfig.from_dict(test_dict)

    def _propogate_source(self):
        self._source["project"] = self._merge(
            self._source["general"], self._source["project"]
        )
        for test_key in self._source["tests"]:
            test = self._merge(self._source["project"], self._source["tests"][test_key])
            self._source["tests"][test_key] = test

    def set_source(
        self, source_name: str, dest: Optional[Any] = None
    ) -> Optional[Union[str, dict]]:
        base_case = False
        if dest is None:
            base_case = True
            self._source = self.to_dict()
            dest = self._source
        if not isinstance(dest, dict):
            return source_name
        if isinstance(dest, dict):
            for item in dest:
                dest[item] = self.set_source(source_name, dest[item])
        if not base_case:
            return dest
        return None

    @classmethod
    def merge(
        cls, base_config: "BaseConfig", merge_config: "BaseConfig"
    ) -> "BaseConfig":

        merged = base_config.to_dict()
        merge_nested_dict(merged, merge_config.to_dict())

        merged_source = base_config._source.copy()
        merge_nested_dict(merged_source, merge_config._source)

        config = cls.from_dict(merged)

        config._source = merged_source
        config._propogate_source()  # pylint: disable=protected-access
        return config
