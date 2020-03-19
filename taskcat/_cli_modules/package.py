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
        source_folder: str = "lambda_functions/source",
        zip_folder: str = "lambda_functions/packages",
        config_file: str = ".taskcat.yml",
    ):
        """
        :param project_root: base path for project
        :param source_folder: folder containing the lambda source files, relative to the
        project_root
        :param zip_folder: folder to output zip files, relative to the project root
        :param config_file: path to taskcat project config file
        """
        project_root_path: Path = Path(project_root).expanduser().resolve()
        project_config: Path = project_root_path / config_file
        config = Config.create(
            project_config_path=project_config,
            project_root=project_root_path,
            args={
                "project": {
                    "lambda_zip_path": zip_folder,
                    "lambda_source_path": source_folder,
                }
            },
        )
        if not config.config.project.package_lambda:
            LOG.info("Lambda packaging disabled by config")
            return
        LambdaBuild(config, project_root_path)
