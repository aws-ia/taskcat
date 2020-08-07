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

        config = Config.create(
            project_root=_project_root,
            project_config_path=Path(_project_root / ".taskcat.yml"),
        )

        amiupdater = AMIUpdater(config=config)
        try:
            amiupdater.update_amis()
        except AMIUpdaterCommitNeededException:
            exit_with_code(100)
        except AMIUpdaterFatalException:
            exit_with_code(1)
