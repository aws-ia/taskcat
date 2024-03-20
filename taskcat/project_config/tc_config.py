import logging
# from pathlib import Path

import yaml
import git
from taskcat.project_config.tools import _add_parameter_values
# from yaml.error import YAMLError

# import pkg_resources
# from taskcat._config import Config

LOG = logging.getLogger(__name__)


class CFTParameter(yaml.YAMLObject):
    """Class representing a Parameter object of the CFN"""

    yaml_tag = '!Parameters'

    def __init__(self, name):
        self.name = name


class TaskCatConfigGenerator:
    def __init__(self, main_template: str, output_file: str, project_root_path: str, owner_email: str, aws_region: str):
        self.output_file = output_file
        self.main_template = main_template
        self.project_root_path = project_root_path
        self.owner_email = owner_email
        self.aws_region = aws_region
        self.repo = git.Repo(project_root_path, search_parent_directories=True)
        self.repo_name = self.repo.remotes.origin.url.split('.git')[0].split('/')[-1]

    def generate_config(self):
        LOG.warning("This is an ALPHA feature. Use with caution")
        yaml.add_multi_constructor('!', lambda loader, suffix, node: None)
        # Read Yaml file
        cfn = yaml.full_load(open(self.main_template, 'r', encoding="utf-8"))
        # Container for each parameter object
        parameters = []
        # Get data for each parameter
        for n in cfn['Parameters']:
            cfn_param = CFTParameter(n)
            for i in cfn['Parameters'][n]:
                setattr(cfn_param, i, cfn['Parameters'][n][i])
            # Append the parameter data to the list
            parameters.append(cfn_param)
        # Create the taskcat.yaml file and write the document
        m = open(f'{self.project_root_path}/.taskcat.yml',
                 "w+",
                 encoding="utf-8")
        m.write("project:\r\n")
        m.write(f"  name: {self.repo_name}\r\n")
        m.write(f"  owner: {self.owner_email}\r\n")
        m.write("  package_lambda: true \r\n")
        m.write("  shorten_stack_name: true \r\n")
        m.write("  s3_regional_buckets: true \r\n")
        m.write("  regions: \r\n")
        m.write(f"    - {self.aws_region}\r\n")
        m.write(f"  template: {self.main_template}\r\n")
        m.write("  parameters:\r\n")
        m.write(_add_parameter_values(parameters))
        m.write("tests:\r\n")
        m.write("  default:\r\n")
        m.write(f"    template: {self.main_template}\r\n")
        m.close()
