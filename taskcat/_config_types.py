import json
import logging
from pathlib import Path
from typing import Dict, Optional, Union

import boto3
import yaml
from jsonschema import exceptions

from taskcat._client_factory import ClientFactory
from taskcat._common_utils import absolute_path, schema_validate as validate
from taskcat._s3_stage import S3APIResponse, S3BucketCreatorException
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class Test:
    def __init__(
        self,
        template_file: Path,
        name: str = "default",
        parameter_input: Path = None,
        parameters: dict = None,
        regions: set = None,
        project_root: Union[Path, str] = "./",
        auth: dict = None,
    ):
        auth = auth if auth is not None else {}
        self._project_root: Path = Path(project_root)
        self.template_file: Path = self._guess_path(template_file)
        self.parameter_input_file: Optional[Path] = None
        if parameter_input:
            self.parameter_input_file = self._guess_path(parameter_input)
        self.parameters: Dict[
            str, Union[str, int, bool]
        ] = self._params_from_file() if parameter_input else {}
        if parameters:
            self.parameters.update(parameters)
        validate(self.parameters, "overrides")
        self.regions: list = list(regions) if regions else []
        self.auth: dict = auth
        self.client_factory: ClientFactory = ClientFactory()
        self.name: str = name

    def _guess_path(self, path):
        abs_path = absolute_path(path)
        if not abs_path:
            abs_path = absolute_path(self._project_root / path)
        if not abs_path:
            abs_path = self._legacy_path_prefix(path)
        if not abs_path:
            raise TaskCatException(
                f"Cannot find {path} with project root" f" {self._project_root}"
            )
        return abs_path

    def _legacy_path_prefix(self, path):
        abs_path = absolute_path(self._project_root / "templates" / path)
        if abs_path:
            LOG.warning(
                "found path with deprecated relative path, support for this will be "
                "removed in future versions, please update %s to templates/%s",
                path,
                path,
            )
            return abs_path
        abs_path = absolute_path(self._project_root / "ci" / path)
        if abs_path:
            LOG.warning(
                "found path with deprecated relative path, support for this will be "
                "removed in future versions, please update %s to ci/%s",
                path,
                path,
            )
        return abs_path

    def _params_from_file(self):
        if not self.parameter_input_file:
            return None
        params = yaml.safe_load(open(str(self.parameter_input_file), "r"))
        self._validate_params(params)
        try:
            validate(params, "legacy_parameters")
            params = self._convert_legacy_params(params)
        except exceptions.ValidationError:
            pass
        return params

    @staticmethod
    def _convert_legacy_params(legacy_params):
        return {p["ParameterKey"]: p["ParameterValue"] for p in legacy_params}

    def _validate_params(self, params):
        try:
            validate(params, "overrides")
        except exceptions.ValidationError as e:
            try:
                validate(params, "legacy_parameters")
                LOG.warning(
                    "%s parameters are in a format that will be deprecated in "
                    "the next version of taskcat",
                    str(self.parameter_input_file),
                )
            except exceptions.ValidationError:
                # raise original exception
                raise e

    @classmethod
    def from_dict(cls, raw_test: dict, project_root="./"):
        raw_test["project_root"] = Path(project_root)
        return Test(**raw_test)


class S3BucketConfig:
    def __init__(self):
        self.name = ""
        self.public = False


class AWSRegionObject:
    def __init__(self, region_name: str, client_factory: ClientFactory):
        self.name: str = region_name
        self.s3bucket: Optional[S3Bucket] = None
        self.account: Optional[str] = None
        self._cf: ClientFactory = client_factory
        self._credset_name: Optional[str] = None
        self._credset_modify = True
        self.partition = None

    @property
    def credset_name(self) -> Optional[str]:
        return self._credset_name

    @credset_name.setter
    def credset_name(self, value: str) -> None:
        if not self._credset_modify:
            return
        self._credset_name = value

    def disable_credset_modification(self):
        self._credset_modify = False

    def client(self, service):
        service_session = self._cf.get(
            credential_set=self.credset_name, region=self.name, service=service
        )
        return service_session

    def set_partition(self):
        if not self._credset_name:
            return
        avail_regions = self._cf.get_session(
            self.credset_name, self.name
        ).get_available_regions("s3")
        if "us-east-1" in avail_regions:
            self.partition = "aws"
        elif "us-gov-east-1" in avail_regions:
            self.partition = "aws-us-gov"
        elif "cn-north-1" in avail_regions:
            self.partition = "aws-cn"

    def get_bucket_region_for_partition(self):
        region = "us-east-1"
        if self.partition == "aws-us-gov":
            region = "us-gov-east-1"
        elif self.partition == "aws-cn":
            region = "cn-north-1"
        return region

    def get_s3_client(self):
        return self._cf.get(
            credential_set=self.credset_name,
            region=self.get_bucket_region_for_partition(),
            service="s3",
        )

    def __repr__(self):
        return f"<AWSRegionObject(region_name={self.name}) object at {hex(id(self))}>"


class S3Bucket:
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        config,
        client: boto3.client,
        name: str = "",
        region: str = "us-east-1",
        auto: bool = True,
        account: str = "",
    ):
        self.name: str = name
        self.public: bool = config.s3bucket.public
        self.tags: list = []
        self.region: str = region
        self.sigv4: bool = True
        self._auto: bool = auto
        self._config = config
        self._client = client
        self._acl = ""
        self._policy: Optional[str] = None
        self._created: bool = False
        self._max_name_len = 63
        # Account
        self.account = account
        # Client
        self._determine_bucket_attributes()

    def _determine_bucket_attributes(self):
        self.sigv4 = not self._config.enable_sig_v2
        self.tags = self._config.tags
        self.public = self._config.s3bucket.public
        if not self.auto:
            self._assert_bucket_exists(self.name)
            self._created = True

    @property
    def acl(self):
        return self._acl

    @property
    def policy(self):
        return self._policy

    @property
    def client(self):
        return self._client

    @property
    def auto(self):
        return self._auto

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
                    "Resource": f"arn:aws:s3:::{self.name}/*",
                    "Condition": {"StringEquals": {"s3:signatureversion": "AWS"}},
                }
            ],
        }
        return json.dumps(policy)

    def _create_in_region(self):
        if self.region == "us-east-1":
            response = self.client.create_bucket(ACL=self.acl, Bucket=self.name)
        else:
            response = self.client.create_bucket(
                ACL=self.acl,
                Bucket=self.name,
                CreateBucketConfiguration={"LocationConstraint": self.region},
            )

        return S3APIResponse(response)

    def _create_bucket(self, bucket_name):
        _create_resp = self._create_in_region()
        if _create_resp.ok:
            LOG.info(f"Staging Bucket: [{bucket_name}]")

        if self.tags:
            LOG.info(f"Propagating tags to this bucket.")
            self.client.put_bucket_tagging(
                Bucket=bucket_name, Tagging={"TagSet": self.tags}
            )

        if self.sigv4:
            LOG.info(f"Enforcing SigV4 requests for bucket ${bucket_name}")
            self.client.put_bucket_policy(Bucket=self.name, Policy=self.sigv4_policy)

    def _assert_bucket_exists(self, name):

        # Verify bucket exists.
        try:
            _ = self.client.list_objects(Bucket=name)
        except self.client.exceptions.NoSuchBucket:
            raise TaskCatException(
                f"The bucket you provided ({name}) does " f"not exist. Exiting."
            )
        return True

    def create(self):
        if self._created:
            return

        # Verify bucket name length
        if len(self.name) > self._max_name_len:
            raise S3BucketCreatorException(
                f"The bucket name you provided [{self._config.s3bucket}] \
                is greater than {self._max_name_len} characters."
            )

        LOG.info(f"Creating bucket in {self.region} for account {self.account}")
        self._create_bucket(self.name)
        self._created = True

    # TODO Add delete().
    def delete(self):
        pass
