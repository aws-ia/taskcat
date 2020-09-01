import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Optional, Union

import yaml
from botocore.exceptions import ClientError

from taskcat._cfn.template import Template, tcat_template_cache
from taskcat._client_factory import Boto3Cache
from taskcat._dataclasses import (
    BaseConfig,
    RegionObj,
    S3BucketObj,
    Tag,
    TestObj,
    TestRegion,
    generate_bucket_name,
    generate_regional_bucket_name,
)
from taskcat._legacy_config import legacy_overrides, parse_legacy_config
from taskcat._template_params import ParamGen
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)

GENERAL = Path("~/.taskcat.yml").expanduser().resolve()
PROJECT = Path("./.taskcat.yml").resolve()
PROJECT_ROOT = Path("./").resolve()
OVERRIDES = Path("./.taskcat_overrides.yml").resolve()

DEFAULTS = {
    "project": {
        "s3_enable_sig_v2": False,
        "build_submodules": True,
        "package_lambda": True,
        "lambda_zip_path": "lambda_functions/packages",
        "lambda_source_path": "lambda_functions/source",
        "shorten_stack_name": False,
    }
}


class Config:
    def __init__(self, sources: list, uid: uuid.UUID, project_root: Path):
        self.config = BaseConfig.from_dict(DEFAULTS)
        self.config.set_source("TASKCAT_DEFAULT")
        self.project_root = project_root
        self.uid = uid
        for source in sources:
            config_dict: dict = source["config"]
            source_name: str = source["source"]
            source_config = BaseConfig.from_dict(config_dict)
            source_config.set_source(source_name)
            self.config = BaseConfig.merge(self.config, source_config)

    @classmethod
    # pylint: disable=too-many-locals
    def create(
        cls,
        template_file: Optional[Path] = None,
        args: Optional[dict] = None,
        global_config_path: Path = GENERAL,
        project_config_path: Path = PROJECT,
        overrides_path: Path = OVERRIDES,
        env_vars: Optional[dict] = None,
        project_root: Path = PROJECT_ROOT,
        uid: uuid.UUID = None,
    ) -> "Config":
        uid = uid if uid else uuid.uuid4()
        project_source = cls._get_project_source(
            cls, project_config_path, project_root, template_file
        )

        # general
        legacy_overrides(
            Path("~/.aws/taskcat_global_override.json").expanduser().resolve(),
            global_config_path,
            "global",
        )
        sources = [
            {
                "source": str(global_config_path),
                "config": cls._dict_from_file(global_config_path),
            }
        ]

        # project config file
        if project_source:
            sources.append(project_source)

        # template file
        if isinstance(template_file, Path):
            sources.append(
                {
                    "source": str(template_file),
                    "config": cls._dict_from_template(template_file),
                }
            )

        # override file
        legacy_overrides(
            project_root / "ci/taskcat_project_override.json", overrides_path, "project"
        )
        if overrides_path.is_file():
            overrides = BaseConfig().to_dict()
            with open(str(overrides_path), "r") as file_handle:
                override_params = yaml.safe_load(file_handle)
            overrides["project"]["parameters"] = override_params
            sources.append({"source": str(overrides_path), "config": overrides})

        # environment variables
        sources.append(
            {
                "source": "EnvoronmentVariable",
                "config": cls._dict_from_env_vars(env_vars),
            }
        )

        # cli arguments
        if args:
            sources.append({"source": "CliArgument", "config": args})
        return cls(sources=sources, uid=uid, project_root=project_root)

    # pylint: disable=protected-access
    @staticmethod
    def _get_project_source(base_cls, project_config_path, project_root, template_file):
        try:
            return {
                "source": str(project_config_path),
                "config": base_cls._dict_from_file(project_config_path, fail_ok=False),
            }
        except FileNotFoundError as e:
            error = e
            try:
                legacy_conf = parse_legacy_config(project_root)
                return {
                    "source": str(project_root / "ci/taskcat.yml"),
                    "config": legacy_conf.to_dict(),
                }
            except Exception as e:  # pylint: disable=broad-except
                LOG.debug(str(e), exc_info=True)
                if not template_file:
                    # pylint: disable=raise-missing-from
                    raise error

    @staticmethod
    def _dict_from_file(file_path: Path, fail_ok=True) -> dict:
        config_dict = BaseConfig().to_dict()
        if not file_path.is_file() and fail_ok:
            return config_dict
        try:
            with open(str(file_path), "r") as file_handle:
                config_dict = yaml.safe_load(file_handle)
            return config_dict
        except Exception as e:  # pylint: disable=broad-except
            LOG.warning(f"failed to load config from {file_path}")
            LOG.debug(str(e), exc_info=True)
            if not fail_ok:
                raise e
        return config_dict

    @staticmethod
    def _dict_from_template(file_path: Path) -> dict:
        relative_path = str(file_path.relative_to(PROJECT_ROOT))
        config_dict = (
            BaseConfig()
            .from_dict(
                {"project": {"template": relative_path}, "tests": {"default": {}}}
            )
            .to_dict()
        )
        if not file_path.is_file():
            raise TaskCatException(f"invalid template path {file_path}")
        try:
            template = Template(
                str(file_path), template_cache=tcat_template_cache
            ).template
        except Exception as e:
            LOG.warning(f"failed to load template from {file_path}")
            LOG.debug(str(e), exc_info=True)
            raise e
        if not template.get("Metadata"):
            return config_dict
        if not template["Metadata"].get("taskcat"):
            return config_dict
        template_config_dict = template["Metadata"]["taskcat"]
        if not template_config_dict.get("project"):
            template_config_dict["project"] = {}
        template_config_dict["project"]["template"] = relative_path
        if not template_config_dict.get("tests"):
            template_config_dict["tests"] = {"default": {}}
        return template_config_dict

    # pylint: disable=protected-access
    @staticmethod
    def _dict_from_env_vars(
        env_vars: Optional[Union[os._Environ, Dict[str, str]]] = None
    ):
        if env_vars is None:
            env_vars = os.environ
        config_dict: Dict[str, Dict[str, Union[str, bool, int]]] = {}
        for key, value in env_vars.items():
            if key.startswith("TASKCAT_"):
                key = key[8:].lower()
                sub_key = None
                key_section = None
                for section in ["general", "project", "tests"]:
                    if key.startswith(section):
                        sub_key = key[len(section) + 1 :]
                        key_section = section
                if isinstance(sub_key, str) and isinstance(key_section, str):
                    if value.isnumeric():
                        value = int(value)
                    elif value.lower() in ["true", "false"]:
                        value = value.lower() == "true"
                    if not config_dict.get(key_section):
                        config_dict[key_section] = {}
                    config_dict[key_section][sub_key] = value
        return config_dict

    def get_regions(self, boto3_cache: Boto3Cache = None):
        if boto3_cache is None:
            boto3_cache = Boto3Cache()

        region_objects: Dict[str, Dict[str, RegionObj]] = {}
        for test_name, test in self.config.tests.items():
            region_objects[test_name] = {}
            for region in test.regions:
                # TODO: comon_utils/determine_profile_for_region
                profile = (
                    test.auth.get(region, test.auth.get("default", "default"))
                    if test.auth
                    else "default"
                )
                region_objects[test_name][region] = RegionObj(
                    name=region,
                    account_id=boto3_cache.account_id(profile),
                    partition=boto3_cache.partition(profile),
                    profile=profile,
                    _boto3_cache=boto3_cache,
                    taskcat_id=self.uid,
                    _role_name=test.role_name,
                )
        return region_objects

    def get_buckets(self, boto3_cache: Boto3Cache = None):
        regions = self.get_regions(boto3_cache)
        bucket_objects: Dict[str, S3BucketObj] = {}
        bucket_mappings: Dict[str, Dict[str, S3BucketObj]] = {}
        for test_name, test in self.config.tests.items():
            bucket_mappings[test_name] = {}
            for region_name, region in regions[test_name].items():
                if test.s3_regional_buckets:
                    bucket_obj = self._create_regional_bucket_obj(
                        bucket_objects, region, test
                    )
                    bucket_objects[f"{region.account_id}{region.name}"] = bucket_obj
                else:
                    bucket_obj = self._create_legacy_bucket_obj(
                        bucket_objects, region, test
                    )
                    bucket_objects[region.account_id] = bucket_obj
                bucket_mappings[test_name][region_name] = bucket_obj

        return bucket_mappings

    def _create_legacy_bucket_obj(self, bucket_objects, region, test):
        new = False
        object_acl = (
            self.config.project.s3_object_acl
            if self.config.project.s3_object_acl
            else "private"
        )
        sigv4 = not self.config.project.s3_enable_sig_v2
        if not test.s3_bucket and not bucket_objects.get(region.account_id):
            name = generate_bucket_name(self.config.project.name)
            auto_generated = True
            new = True
        elif bucket_objects.get(region.account_id):
            name = bucket_objects[region.account_id].name
            auto_generated = bucket_objects[region.account_id].auto_generated
        else:
            name = test.s3_bucket
            auto_generated = False
        bucket_region = self._get_bucket_region_for_partition(region.partition)
        bucket_obj = S3BucketObj(
            name=name,
            region=bucket_region,
            account_id=region.account_id,
            s3_client=region.session.client("s3", region_name=bucket_region),
            auto_generated=auto_generated,
            object_acl=object_acl,
            sigv4=sigv4,
            taskcat_id=self.uid,
            partition=region.partition,
            regional_buckets=test.s3_regional_buckets,
        )
        if new:
            bucket_obj.create()
        return bucket_obj

    def _create_regional_bucket_obj(self, bucket_objects, region, test):
        _bucket_obj_key = f"{region.account_id}{region.name}"
        new = False
        object_acl = (
            self.config.project.s3_object_acl
            if self.config.project.s3_object_acl
            else "private"
        )
        sigv4 = not self.config.project.s3_enable_sig_v2
        if not test.s3_bucket and not bucket_objects.get(_bucket_obj_key):
            name = generate_regional_bucket_name(region)
            auto_generated = True
            new = True
        elif bucket_objects.get(_bucket_obj_key):
            name = bucket_objects[_bucket_obj_key].name
            auto_generated = bucket_objects[_bucket_obj_key].auto_generated
        else:
            name = f"{test.s3_bucket}-{region.name}"
            auto_generated = False
            try:
                region.client("s3").head_bucket(Bucket=name)
            except ClientError as e:
                if "(404)" in str(e):
                    new = True
                else:
                    raise
        bucket_obj = S3BucketObj(
            name=name,
            region=region.name,
            account_id=region.account_id,
            s3_client=region.session.client("s3", region_name=region.name),
            auto_generated=auto_generated,
            object_acl=object_acl,
            sigv4=sigv4,
            taskcat_id=self.uid,
            partition=region.partition,
            regional_buckets=test.s3_regional_buckets,
        )
        if new:
            bucket_obj.create()
        return bucket_obj

    @staticmethod
    def _get_bucket_region_for_partition(partition):
        region = "us-east-1"
        if partition == "aws-us-gov":
            region = "us-gov-east-1"
        elif partition == "aws-cn":
            region = "cn-north-1"
        return region

    def get_rendered_parameters(self, bucket_objects, region_objects, template_objects):
        parameters = {}
        template_params = self.get_params_from_templates(template_objects)
        for test_name, test in self.config.tests.items():
            parameters[test_name] = {}
            for region_name in test.regions:
                region_params = template_params[test_name].copy()
                for param_key, param_value in test.parameters.items():
                    if param_key in region_params:
                        region_params[param_key] = param_value
                region = region_objects[test_name][region_name]
                s3bucket = bucket_objects[test_name][region_name]
                parameters[test_name][region_name] = ParamGen(
                    region_params,
                    s3bucket.name,
                    region.name,
                    region.client,
                    self.config.project.name,
                    test_name,
                    test.az_blacklist,
                ).results
        return parameters

    @staticmethod
    def get_params_from_templates(template_objects):
        parameters = {}
        for test_name, template in template_objects.items():
            parameters[test_name] = template.parameters()
        return parameters

    def get_templates(self):
        templates = {}
        for test_name, test in self.config.tests.items():
            templates[test_name] = Template(
                template_path=self.project_root / test.template,
                project_root=self.project_root,
                s3_key_prefix=f"{self.config.project.name}/",
                template_cache=tcat_template_cache,
            )
        return templates

    def get_tests(self, templates, regions, buckets, parameters):
        tests = {}
        for test_name, test in self.config.tests.items():
            region_list = []
            tag_list = []
            if test.tags:
                for tag_key, tag_value in test.tags.items():
                    tag_list.append(Tag({"Key": tag_key, "Value": tag_value}))
            for region_obj in regions[test_name].values():
                region_list.append(
                    TestRegion.from_region_obj(
                        region_obj,
                        buckets[test_name][region_obj.name],
                        parameters[test_name][region_obj.name],
                    )
                )

            tests[test_name] = TestObj(
                name=test_name,
                template_path=self.project_root / test.template,
                template=templates[test_name],
                project_root=self.project_root,
                regions=region_list,
                tags=tag_list,
                uid=self.uid,
                _project_name=self.config.project.name,
                _shorten_stack_name=self.config.project.shorten_stack_name,
            )
        return tests
