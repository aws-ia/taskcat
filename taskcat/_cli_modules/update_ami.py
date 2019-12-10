import logging
import os
from pathlib import Path

from taskcat._amiupdater import (
    AMIUpdater,
    AMIUpdaterCommitNeededException,
    AMIUpdaterFatalException,
)
from taskcat._client_factory import Boto3Cache
from taskcat._common_utils import exit_with_code, neglect_submodule_templates
from taskcat._config import Config

LOG = logging.getLogger(__name__)


class UpdateAMI:
    """
    Updates AMI IDs within CloudFormation templates
    """

    CLINAME = "update-ami"

    def __init__(self, project_root: str = "./"):
        """
        :param project_root: base path for project
        """

        if project_root == "./":
            _project_root = Path(os.getcwd())
        else:
            _project_root = Path(project_root)

        _c = Config.create(project_config_path=Path(_project_root / ".taskcat.yml"))
        _boto3cache = Boto3Cache()

        # Stripping out any test-specific regions/auth.
        config_dict = _c.config.to_dict()
        for _, test_config in config_dict["tests"].items():
            if test_config.get("auth", None):
                del test_config["auth"]
            if test_config.get("regions", None):
                del test_config["regions"]
        new_config = Config.create(
            project_config_path=Path(_project_root / ".taskcat.yml"), args=config_dict
        )

        # Fetching the region objects.
        regions = new_config.get_regions(boto3_cache=_boto3cache)
        region_key = list(regions.keys())[0]

        unprocessed_templates = new_config.get_templates(
            project_root=Path(_project_root)
        ).values()
        finalized_templates = neglect_submodule_templates(
            project_root=Path(_project_root), template_list=unprocessed_templates
        )

        amiupdater = AMIUpdater(
            template_list=finalized_templates,
            regions=regions[region_key],
            boto3cache=_boto3cache,
        )
        try:
            amiupdater.update_amis()
        except AMIUpdaterCommitNeededException:
            exit_with_code(100)
        except AMIUpdaterFatalException:
            exit_with_code(1)
