import logging
import git
# from pathlib import Path
from ruamel.yaml.comments import CommentedMap as OrderedDict
# from ruamel.yaml.main import round_trip_dump as yaml_dump
from ruamel.yaml import YAML
from taskcat.project_config.tools import _add_parameter_values, _get_parameter_stats

yaml = YAML()
yaml.preserve_quotes = True
LOG = logging.getLogger(__name__)


class TaskCatConfigGenerator:
    def __init__(
            self, main_template: str, output_file: str,
            project_root_path: str, owner_email: str,
            aws_region: str, create_overrides_file: bool):
        self.output_file = output_file
        self.main_template = main_template
        self.project_root_path = project_root_path
        self.owner_email = owner_email
        self.aws_region = aws_region
        self.create_overrides_file = create_overrides_file
        self.repo = git.Repo(project_root_path, search_parent_directories=True)
        self.repo_name = self.repo.remotes.origin.url.split('.git')[0].split('/')[-1]

    def generate_config(self):
        LOG.warning("This is an ALPHA feature. Use with caution")
        # Read Yaml file
        cfn = yaml.load(open(self.main_template, 'r', encoding="utf-8"))
        # Container for each parameter object
        parameters = {}
        # Get data for each parameter
        for n in cfn['Parameters']:
            parameters[n] = cfn['Parameters'][n]
        # Create a dict for the config content
        cfg_dict = OrderedDict({
            "project": OrderedDict({
                "name": self.repo_name,
                "owner": self.owner_email,
                "package_lambda": "true",
                "shorten_stack_name": "true",
                "s3_regional_buckets": "true",
                "regions": [self.aws_region],
                "parameters": _add_parameter_values(parameters)
            }),
            "tests": OrderedDict({
                "default": OrderedDict({
                    "template": self.main_template
                })
            })
        })
        with open(f'{self.project_root_path}/{self.output_file}',
                  "w+", encoding="utf-8") as outfile:
            yaml.dump(cfg_dict, outfile)
        outfile.close()
        print(_get_parameter_stats(cfg_dict['project']['parameters']))
        # # Create the .taskcat_overrides.yaml file and write the document
        if self.create_overrides_file:
            with open(f'{self.project_root_path}//.taskcat_overrides.yml',
                      "w+", encoding="utf-8") as outfile:
                yaml.dump(cfg_dict["project"]["parameters"], outfile)
        outfile.close()
