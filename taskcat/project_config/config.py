import logging
import os
import sys
from pathlib import Path
from typing import OrderedDict

import yaml

import git
from taskcat._cfn.template import Template
from taskcat._config import Config
from taskcat.exceptions import TaskCatException
from taskcat.project_config.tools import _get_parameter_stats

LOG = logging.getLogger(__name__)
LOG_CONFIG = logging.getLogger("taskcat._config")
LOG_CONFIG.setLevel(logging.ERROR)


class ConfigGenerator:
    def __init__(
        self,
        main_template: str,
        output_file: str,
        project_root_path: str,
        owner_email: str,
        aws_region: str,
        replace: bool,
    ):
        self.output_file = output_file
        self.main_template = main_template
        self.project_root_path = project_root_path
        self.owner_email = owner_email
        self.aws_region = aws_region
        self.repo = git.Repo(project_root_path, search_parent_directories=True)
        self.repo_name = self.repo.remotes.origin.url.split(".git")[0].split("/")[-1]
        self.replace = replace

    def generate_config(self):
        base_path = Path(self.project_root_path).resolve()
        template_path = base_path / self.main_template
        project_config_path = base_path / self.output_file
        global_config_path = base_path / "./.taskcat_global.yml"

        # Check that the provided paths are valid and return an error if they are not
        if not base_path.exists():
            raise TaskCatException(f"Base path {base_path} does not exist")
        if not template_path.exists():
            raise TaskCatException(f"Template file {template_path} does not exist")

        LOG.warning("This is an ALPHA feature. Use with caution")
        # Read Yaml file

        cfn = Template(template_path, base_path, "", "")

        # Create a dict for the config content
        params = {}
        for k, v in cfn.parameters().items():
            if v is not None:
                params[k] = v
        cfg_dict = OrderedDict(
            {
                "project": OrderedDict(
                    {
                        "name": self.repo_name,
                        "owner": self.owner_email,
                        "regions": [self.aws_region],
                        "parameters": params,
                    }
                ),
                "tests": OrderedDict(
                    {"default": OrderedDict({"template": self.main_template})}
                ),
            }
        )

        # Config File Handling
        config_file = Path(project_config_path)
        if config_file.exists():
            # Check if file is empty
            if os.stat(project_config_path).st_size == 0:
                LOG.warning("Empty project config found. " "Overwriting...")
                os.remove(project_config_path)
            elif os.stat(project_config_path).st_size > 0 and not self.replace:
                raise TaskCatException(
                    "Project config file already exists. "
                    "No changes will be made. "
                    "to override use --replace flag"
                )
            else:
                LOG.warning(
                    "Project config file already exists. " "Overwriting existing file"
                )
                os.remove(project_config_path)
        try:
            config = Config.create(
                args=cfg_dict,
                template_file=template_path,
                project_config_path=project_config_path,
                global_config_path=global_config_path,
                env_vars={
                    "TASKCAT_PROJECT_PACKAGE_LAMBDA": "True",
                    "TASKCAT_PROJECT_SHORTEN_STACK_NAME": "True",
                    "TASKCAT_PROJECT_S3_REGIONAL_BUCKETS": "True",
                },
            )
            LOG.info("Config file created successfully")
        except TaskCatException as e:
            LOG.error(e)
            sys.exit(1)

        with open(
            f"{self.project_root_path}/{self.output_file}", "w+", encoding="utf-8"
        ) as outfile:
            config_dict = config.config.to_dict()
            config_dict.pop("general")
            yaml.dump(config_dict, outfile)
        outfile.close()
        LOG.info(_get_parameter_stats(cfg_dict["project"]["parameters"]))
