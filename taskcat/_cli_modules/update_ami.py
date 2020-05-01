import logging
import os
from pathlib import Path

from taskcat._amiupdater import (
    AMIUpdater,
    AMIUpdaterCommitNeededException,
    AMIUpdaterFatalException,
)
from taskcat._common_utils import exit_with_code
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

        _c = Config.create(
            project_root=_project_root,
            project_config_path=Path(_project_root / ".taskcat.yml"),
        )

        # Stripping out any test-specific regions/auth.
        config_dict = _c.config.to_dict()
        for _, test_config in config_dict["tests"].items():
            if test_config.get("auth", None):
                del test_config["auth"]
            if test_config.get("regions", None):
                del test_config["regions"]
        new_config = Config.create(
            project_root=_project_root,
            project_config_path=Path(_project_root / ".taskcat.yml"),
            args=config_dict,
        )

        amiupdater = AMIUpdater(config=new_config)
        try:
            amiupdater.update_amis()
        except AMIUpdaterCommitNeededException:
            exit_with_code(100)
        except AMIUpdaterFatalException:
            exit_with_code(1)
