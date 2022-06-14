import logging
import tempfile
from pathlib import Path

import yaml

from taskcat._config import PROJECT, Config
from taskcat._lambda_build import LambdaBuild

LOG = logging.getLogger(__name__)


class PackageSingle:
    """packages lambda source files into zip files. If a dockerfile is present in a
    source folder, it will be run prior to zipping the contents"""

    CLINAME = "package-single"

    def __init__(
        self,
        project_root: str = "./",
        source_folder: str = "lambda_functions/source",
        zip_folder: str = "lambda_functions/packages",
        from_ref: str = None,
        to_ref: str = None,
        name: str = None,
    ):
        """
        :param project_root: base path for project
        :param source_folder: folder containing the lambda source files, relative to the
        project_root
        :param zip_folder: folder to output zip files, relative to the project root
        :param config_file: path to taskcat project config file
        """
        project_root_path: Path = Path(project_root).expanduser().resolve()
        if not PROJECT.exists():
            _fd, _path = tempfile.mkstemp()
            _path = Path(_path).expanduser().resolve()
            _d = {"project": {"name": "blah", "regions": ["us-east-1"]}}
            with open(_path, "w", encoding="utf8") as _f:
                _f.write(yaml.dump(_d))
            _pc = _path

        config = Config.create(
            project_config_path=_pc if _pc else None,
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
        LambdaBuild(config, project_root_path, from_ref, to_ref, name)
