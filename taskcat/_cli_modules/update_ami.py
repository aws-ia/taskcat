import logging
<<<<<<< HEAD
import os
from taskcat._config import Config
from taskcat._client_factory import Boto3Cache
from taskcat._amiupdater import AMIUpdater
from taskcat._common_utils import neglect_submodule_templates
=======
from taskcat._config import Config
from taskcat._client_factory import Boto3Cache
from taskcat.exceptions import TaskCatException
from dulwich.config import ConfigFile, parse_submodules
>>>>>>> 30e3e01... Addding logic for update-ami CLI entrypoint
from pathlib import Path

LOG = logging.getLogger(__name__)


class UpdateAMI:
<<<<<<< HEAD
    """
    Updates AMI IDs within CloudFormation templates
    """

    CLINAME = "update-ami"

    def __init__(self, project_root: str = "./"):
        """
        :param project_root: base path for project
        """

        if project_root == "./":
            project_root = Path(os.getcwd())
        else:
            project_root = Path(project_root)

        config_obj_args = {
            'project_config_path': Path(project_root / '.taskcat.yml')
        }
=======

    def __init__(self, project_root: str = "./"):
        """
        :param input_file: path to project config or CloudFormation template
        :param project_root: base path for project
        """

        config_obj_args = {
                'project_config_path': Path(project_root/'.taskcat.yml')
        }

>>>>>>> 30e3e01... Addding logic for update-ami CLI entrypoint
        c = Config.create(**config_obj_args)
        _boto3cache = Boto3Cache()

        # Stripping out any test-specific regions/auth.
        config_dict = c.config.to_dict()
<<<<<<< HEAD
        for _, test_config in config_dict['tests'].items():
            if test_config.get('auth', None):
                del test_config['auth']
            if test_config.get('regions', None):
                del test_config['regions']
=======
        for test_name, test_config in config_dict['tests'].items():
            del test_config['auth']
            del test_config['regions']
>>>>>>> 30e3e01... Addding logic for update-ami CLI entrypoint
        new_config = Config.create(**config_obj_args, args=config_dict)

        # Fetching the region objects.
        regions = new_config.get_regions(boto3_cache=_boto3cache)
        rk = list(regions.keys())[0]
<<<<<<< HEAD

        unprocessed_templates = new_config.get_templates(
                project_root=Path(project_root),
                boto3_cache=_boto3cache)
        finalized_templates = neglect_submodule_templates(
            project_root=Path(project_root),
            template_list=unprocessed_templates
        )

        amiupdater = AMIUpdater(template_list=finalized_templates, regions=regions[rk], boto3cache=_boto3cache)
        amiupdater.update_amis()
=======
        regions = regions[rk]

        # Fetching the template objects.
        _template_dict = {}
        _templates = new_config.get_templates(
                project_root=Path(project_root),
                boto3_cache=_boto3cache)

        ## one template object per path.
        for _template in _templates.values():
            _template_dict[_template.template_path] = _template
            for _template_descendent in _template.descendents:
                _template_dict[_template_descendent.template_path] = _template_descendent

        # Removing those within a submodule.
        submodule_path_prefixes = []
        gitmodule_config = ConfigFile.from_path(Path(project_root/'.gitmodules'))

        for submodule_path, _, _ in parse_submodules(gitmodule_config):
            submodule_path_prefixes.append(Path(project_root/submodule_path.decode('utf-8')))

        finalized_templates = []
        for template_obj in _template_dict.values():
            gitmodule_template = False
            for gm_path in submodule_path_prefixes:
                if gm_path in template_obj.template_path.parents:
                    gitmodule_template = True
            if not gitmodule_template:
                finalized_templates.append(template_obj)

        return False
#        amiupdater = AMIUpdater(templates=finalized_templates, regions=regions)
#        amiupdater.update_amis()
#
#        errors = lint.lints[1]
#        lint.output_results()
#        if errors or not lint.passed:
#            raise TaskCatException("Lint failed with errors")
>>>>>>> 30e3e01... Addding logic for update-ami CLI entrypoint
