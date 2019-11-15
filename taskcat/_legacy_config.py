import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml

from dataclasses_jsonschema import JsonSchemaMixin
from taskcat._dataclasses import BaseConfig
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


@dataclass
class LegacyGlobalConfig(JsonSchemaMixin):
    qsname: str
    govcloud: bool = field(default=False)
    marketplace_ami: bool = field(default=False)
    owner: str = field(default="")
    regions: List[str] = field(default_factory=list)
    reporting: bool = field(default=True)
    lambda_build: bool = field(default=False)
    s3bucket: str = field(default="")


@dataclass
class LegacyTestConfig(JsonSchemaMixin):
    template_file: str
    parameter_input: str
    regions: List[str] = field(default_factory=list)


@dataclass
class LegacyConfig(JsonSchemaMixin):
    global_: LegacyGlobalConfig
    tests: Dict[str, LegacyTestConfig]


def parse_legacy_config(project_root: Path):
    config_file = (project_root / "ci/taskcat.yml").expanduser().resolve()
    if not config_file.is_file():
        raise TaskCatException(f"No config_file at {config_file}")
    with open(str(config_file), "r") as file_handle:
        config_dict = yaml.safe_load(file_handle)
    # need to rename global key, as it's a python keyword
    config_dict["global_"] = config_dict.pop("global")
    legacy_config = LegacyConfig.from_dict(config_dict)
    tests = {}
    for test_name, test_data in legacy_config.tests.items():
        parameters = {}
        parameter_file = project_root / "ci/" / test_data.parameter_input
        parameter_file = parameter_file.expanduser().resolve()
        with open(str(parameter_file), "r") as file_handle:
            for param in yaml.safe_load(file_handle):
                parameters[param["ParameterKey"]] = param["ParameterValue"]
        tests[test_name] = {
            "template": "templates/" + test_data.template_file,
            "parameters": parameters,
            "regions": test_data.regions,
        }
        if not tests[test_name]["regions"]:
            del tests[test_name]["regions"]
    new_config_dict = {
        "project": {
            "name": legacy_config.global_.qsname,
            "owner": legacy_config.global_.owner,
            "s3_bucket": legacy_config.global_.s3bucket,
            "package_lambda": legacy_config.global_.lambda_build,
            "regions": legacy_config.global_.regions,
        },
        "tests": tests,
    }
    new_config = BaseConfig.from_dict(new_config_dict)
    LOG.warning(
        "config is in a legacy format, support for which will be dropped in a "
        "future version. a new format config (.taskcat.yml) will been placed "
        "in your project_root"
    )
    new_config_path = project_root / ".taskcat.yml"
    if new_config_path.exists():
        LOG.warning(
            f"skipping new config file creation, file already exits at "
            f"{new_config_path}"
        )
    else:
        with open(str(new_config_path), "w") as file_handle:
            config_dict = new_config.to_dict()
            config_dict.pop("general")
            yaml.dump(config_dict, file_handle, default_flow_style=False)
    return new_config


def legacy_overrides(legacy_override, overrides_path, override_type):
    if legacy_override.is_file():
        with open(str(legacy_override), "r") as file_handle:
            override_params = yaml.safe_load(file_handle)
        LOG.warning(
            f"overrides file {str(legacy_override)} is in legacy "
            f"format, support for this format will be deprecated "
            f"in a future version."
        )
        override_params = {
            i["ParameterKey"]: i["ParameterValue"] for i in override_params
        }
        if override_type == "global":
            override_params = {"general": {"parameters": override_params}}
        if not overrides_path.exists():
            LOG.warning(
                f"Converting overrides to new format and saving in " f"{overrides_path}"
            )
            with open(str(overrides_path), "w") as file_handle:
                file_handle.write(yaml.dump(override_params, default_flow_style=False))
        else:
            LOG.warning(
                f"Ignoring legacy overrides as a current format "
                f"file has been found in {str(overrides_path)}"
            )
