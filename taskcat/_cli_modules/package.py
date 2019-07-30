import logging
from pathlib import Path

from taskcat._config import Config
from taskcat._lambda_build import LambdaBuild

LOG = logging.getLogger(__name__)


class Package:
    """packages lambda source files into zip files. If a dockerfile is present in a
    source folder, it will be run prior to zipping the contents"""

    def __init__(
        self,
        project_root: str = "./",
        source_folder: str = "functions/source",
        zip_folder: str = "functions/packages",
        config_file: str = ".taskcat.yml",
    ):
        """
        :param project_root: base path for project
        :param source_folder: folder containing the lambda source files, relative to the
        project_root
        :param zip_folder: folder to output zip files, relative to the project root
        :param config_file: path to taskcat project config file
        """
        config = Config(
            project_config_path=config_file,
            project_root=project_root,
            create_clients=False,
        )
        config.lambda_source_path = (
            Path(config.project_root) / source_folder
        ).resolve()
        config.lambda_zip_path = (Path(config.project_root) / zip_folder).resolve()
        LambdaBuild(config)
