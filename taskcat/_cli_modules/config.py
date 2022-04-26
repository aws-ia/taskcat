import logging
from pathlib import Path

from taskcat._legacy_config import parse_legacy_config

LOG = logging.getLogger(__name__)


class ConvertConfig:
    """
    Mutating actions regarding the config file
    """

    CLINAME = "config"

    @staticmethod
    def convert(
        project_root: str = "./",
    ):  # pylint: disable=too-many-locals
        """Converts config from legacy to new format."""
        project_root_path: Path = Path(project_root).expanduser().resolve()
        parse_legacy_config(project_root_path)
