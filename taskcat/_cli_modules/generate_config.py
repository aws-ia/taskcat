import logging
from pathlib import Path

from taskcat.exceptions import TaskCatException
from taskcat.project_config.config import ConfigGenerator

LOG = logging.getLogger(__name__)


class GenerateConfig:
    """
    [ALPHA] Introspects CFN Template(s) and generates a taskcat configuration file
    necessary to successfully run taskcat.
    """

    CLINAME = "generate-config"

    def __init__(
        self,
        output_file: str = ".taskcat.yml",
        main_template: str = "./templates/template.yaml",
        user_email: str = "noreply@example.com",
        project_root: str = "./",
        aws_region: str = "us-east-1",
        replace: bool = False,
    ):

        project_root_path = Path(project_root).expanduser().resolve()
        if not project_root_path.exists():
            raise TaskCatException(
                f"Project root path {project_root_path} does not exist"
            )
        ConfigGenerator(
            main_template=main_template,
            output_file=output_file,
            project_root_path=str(project_root_path),
            owner_email=user_email,
            aws_region=aws_region,
            replace=replace,
        ).generate_config()
