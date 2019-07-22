import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import yaml

import cfnlint
from taskcat._cfn.template import Template
from taskcat._client_factory import ClientFactory
from taskcat._common_utils import absolute_path, schema_validate as validate
from taskcat._config_types import S3BucketConfig, Test
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)

# TODO: build a mechanism to identify the source of a config value


class Config:  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """
    Config hierarchy (items lower down override items above them):
    global config
    project config
    template config
    ENV vars
    CLI args
    Override file (for parameter overrides)
    """

    DEFAULT_PROJECT_PATHS = [
        "./.taskcat.yml",
        "./.taskcat.yaml",
        "./ci/taskcat.yaml",
        "./ci/taskcat.yml",
    ]

    def __init__(  # pylint: disable=too-many-statements
        self,
        args: Optional[dict] = None,
        global_config_path: str = "~/.taskcat.yml",
        project_config_path: str = None,
        project_root: str = "./",
        override_file: str = None,
        all_env_vars: Optional[List[dict]] = None,
        client_factory=ClientFactory,
    ):  # pylint: disable=too-many-arguments
        # inputs
        if absolute_path(project_config_path) and not Path(project_root).is_absolute():
            project_root = absolute_path(project_config_path).parent / project_root
        self.project_root: Union[Path, str] = absolute_path(project_root)
        self.args: dict = args if args else {}
        self.global_config_path: Optional[Path] = absolute_path(global_config_path)
        self.override_file: Optional[Path] = self._absolute_path(override_file)
        self._client_factory_class = client_factory

        # general config
        self.profile_name: str = ""
        self.aws_access_key: str = ""
        self.aws_secret_key: str = ""
        self.no_cleanup: bool = False
        self.no_cleanup_failed: bool = False
        self.public_s3_bucket: bool = False
        self.verbosity: str = "DEBUG"
        self.tags: dict = {}
        self.stack_prefix: str = ""
        self.lint: bool = False
        self.upload_only: bool = False
        self.lambda_build_only: bool = False
        self.exclude: str = ""
        self.enable_sig_v2: bool = False
        self.auth: Dict[str, dict] = {}

        # project config
        self.name: str = ""
        self.owner: str = ""
        self.package_lambda: bool = True
        self.s3_bucket: S3BucketConfig = S3BucketConfig()
        self.tests: Dict[str, Test] = {}
        self.regions: Set[str] = set()
        self.env_vars: Dict[str, str] = {}
        self.project_config_path: Optional[Path] = None
        self.template_path: Optional[Path] = None
        self.lambda_source_path: Path = (
            Path(self.project_root) / "functions/source/"
        ).resolve()
        self.lambda_zip_path: Path = (
            Path(self.project_root) / "functions/packages/"
        ).resolve()
        self.build_submodules = True
        self._harvest_env_vars(all_env_vars if all_env_vars else os.environ.items())
        self._process_global_config()

        if not self._absolute_path(project_config_path):
            raise TaskCatException(
                f"failed to load project config file {project_config_path}. file "
                f"does not exist"
            )

        if self._is_template(self._absolute_path(project_config_path)):
            self.template_path = self._absolute_path(project_config_path)
            self._process_template_config()
        else:
            self._parse_project_config(project_config_path)
            self._process_project_config()

        self._process_env_vars()
        self._process_args()
        if not self.template_path and not self.tests:
            raise TaskCatException(
                "minimal config requires at least one test or a "
                "template_path to be defined"
            )

        # build client_factory_instances
        self._build_boto_factories()

        # build and attach template objects
        self._get_templates()

    @staticmethod
    def _is_template(path):
        parsed_file = cfnlint.decode.cfn_yaml.load(str(path))
        return "Resources" in parsed_file

    def _get_templates(self):
        for _, test in self.tests.items():
            test.template = Template(
                template_path=test.template_file,
                project_root=self.project_root,
                client_factory_instance=test.client_factory,
            )

    def _build_cred_dict(self):
        creds = {}
        for cred_type in ["aws_secret_key", "aws_access_key", "profile_name"]:
            cred_val = getattr(self, cred_type)
            if cred_val:
                creds[cred_type] = cred_val
        return creds

    @staticmethod
    def _cred_merge(creds, regional):
        if "regional_cred_map" not in creds:
            creds["regional_cred_map"] = {}
        if "default" in regional:
            creds = regional["default"]
            del regional["default"]
        creds["regional_cred_map"].update(regional)
        return creds

    def _build_boto_factories(self):
        instance_cache = []

        def get_instance(provided_creds):
            for creds, instance in instance_cache:
                if provided_creds == creds:
                    return instance
            instance = self._client_factory_class(**provided_creds)
            instance_cache.append([provided_creds, instance])
            return instance

        default_creds = self._cred_merge(self._build_cred_dict(), self.auth.copy())

        for _, test in self.tests.items():
            test_creds = default_creds.copy()
            test_creds["regional_cred_map"] = default_creds["regional_cred_map"].copy()
            if test.auth:
                test_creds = self._cred_merge(test_creds, test.auth.copy())
            test.client_factory = get_instance(test_creds)
            self._propagate_regions(test)

    def _parse_project_config(self, project_config_path):
        self.project_config_path = self._absolute_path(project_config_path)
        if self.project_config_path is None:
            for path in Config.DEFAULT_PROJECT_PATHS:
                try:
                    self.project_config_path = self._absolute_path(path)
                    LOG.debug("found project config in default location %s", path)
                    break
                except TaskCatException:
                    LOG.debug("didn't find project config in %s", path)

    def _absolute_path(self, path: Optional[Union[str, Path]]) -> Optional[Path]:
        if path is None:
            return path
        path = Path(path)
        abs_path = absolute_path(path)
        if self.project_root and not abs_path:
            abs_path = absolute_path(Path(self.project_root) / Path(path))
        if not abs_path:
            raise TaskCatException(
                f"Unable to resolve path {path}, with project_root "
                f"{self.project_root}"
            )
        return abs_path

    def _set(self, opt, val):
        if opt in ["project", "general"]:
            for k, v in val.items():
                self._set(k, v)
            return
        if opt not in self.__dict__:
            raise ValueError(f"{opt} is not a valid config option")
        setattr(self, opt, val)

    def _set_all(self, config: dict):
        for k, v in config.items():
            self._set(k, v)

    def _propagate_regions(self, test: Test):
        default_region = test.client_factory.get_default_region(None, None, None, None)
        if not test.regions and not default_region and not self.regions:
            raise TaskCatException(
                f"unable to define region for test {test.name}, you must define "
                f"regions "
                f"or set a default region in the aws cli"
            )
        if not test.regions:
            if self.regions:
                test.regions = list(self.regions)
            else:
                test.regions = [default_region]

    def _process_global_config(self):
        if self.global_config_path is None:
            return
        instance = yaml.safe_load(open(str(self.global_config_path), "r"))
        validate(instance, "global_config")
        self._set_all(instance)

    def _process_project_config(self):
        if self.project_config_path is None:
            return
        with open(str(self.project_config_path), "r") as file_handle:
            instance = yaml.safe_load(file_handle)
        if "tests" in instance.keys():
            tests = {}
            for test in instance["tests"].keys():
                tests[test] = Test.from_dict(
                    instance["tests"][test], project_root=self.project_root
                )
            instance["tests"] = tests
        if "global" in instance.keys():
            self._process_legacy_project(instance)
        validate(instance, "project_config")
        self._set_all(instance)

    def _process_legacy_project(  # pylint: disable=useless-return
        self, instance
    ) -> Optional[Exception]:
        validate(instance, "legacy_project_config")
        LOG.warning(
            "%s config file is in a format that will be deprecated in the next "
            "version of taskcat",
            str(self.project_config_path),
        )
        # rename global to project
        if "global" in instance:
            instance["project"] = instance["global"]
            del instance["global"]
        if "project" in instance:
            # delete unneeded config items
            for del_item in ["marketplace-ami", "reporting"]:
                if del_item in instance["project"]:
                    del instance["project"][del_item]
            # rename items with new keys
            for rename_item in [
                ["qsname", "name"],
                ["package-lambda", "package_lambda"],
            ]:
                if rename_item[0] in instance["project"]:
                    instance["project"][rename_item[1]] = instance["project"][
                        rename_item[0]
                    ]
                    del instance["project"][rename_item[0]]
        return None

    def _process_template_config(self):
        if not self.template_path:
            return
        template = Template(str(self.template_path)).template
        try:
            template_config = template["Metadata"]["taskcat"]
        except KeyError:
            region = self._client_factory_class().get_default_region(
                None, None, None, None
            )
            name = self.template_path.name.split(".")[0]
            template_config = {
                "project": {"name": name},
                "tests": {name: {"regions": [region]}, "parameters": {}},
            }
        self._add_template_path(template_config)
        validate(template_config, "project_config")
        self._set_all(template_config)

    def _add_template_path(self, template_config):
        if "tests" in template_config.keys():
            for test in template_config["tests"].keys():
                if "template_file" not in template_config["tests"][test].keys():
                    rel_path = str(self.template_path.relative_to(self.project_root))
                    template_config["tests"][test]["template_file"] = rel_path
                template_config["tests"][test] = Test.from_dict(
                    template_config["tests"][test], project_root=self.project_root
                )

    def _process_env_vars(self):
        self._to_project(self.env_vars)
        self._to_tests(self.env_vars)
        self._to_general(self.env_vars)
        if not self.env_vars:
            return
        validate(self.env_vars, "project_config")
        self._set_all(self.env_vars)

    def _process_args(self):
        self._to_project(self.args)
        self._to_tests(self.args)
        self._to_general(self.args)
        if not self.args:
            return
        validate(self.args, "project_config")
        self._set_all(self.args)

    @staticmethod
    def _to_project(args: dict):
        for arg in args.keys():
            if arg.startswith("project_"):
                if "project" not in args.keys():
                    args["project"] = {}
                args["project"][arg[8:]] = args[arg]
                del args[arg]

    def _to_tests(self, args: dict):
        if (
            "template_file" in args.keys()
            or "parameter_input" in args.keys()
            or "regions" in args.keys()
        ):
            template_file = (
                args["template_file"] if "template_file" in args.keys() else None
            )
            parameter_input = (
                args["parameter_input"] if "parameter_input" in args.keys() else None
            )
            regions = (
                set(args["regions"].split(",")) if "regions" in args.keys() else set()
            )
            test = Test(
                template_file=template_file,
                parameter_input=parameter_input,
                regions=regions,
                project_root=self.project_root,
            )
            args["tests"] = {"default": test}
            del args["template_file"]
            del args["parameter_input"]

    @staticmethod
    def _to_general(args: dict):
        for arg in args.keys():
            if "general" not in args.keys():
                args["general"] = {}
            args["general"][arg] = args[arg]
            del args[arg]

    def _harvest_env_vars(self, env_vars):
        for key, value in env_vars:
            if key.startswith("TASKCAT_"):
                key = key[8:].lower()
                if value.isnumeric():
                    value = int(value)
                elif value.lower() in ["true", "false"]:
                    value = value.lower() == "true"
                self.env_vars[key] = value
