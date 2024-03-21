import logging
from pathlib import Path

from taskcat.project_config.tc_config import TaskCatConfigGenerator

LOG = logging.getLogger(__name__)


class GenerateTCConfig:
    """
    [ALPHA] Introspects CFN Template(s) and generates a taskcat configuration file
    necessary to successfully run taskcat.
    """

    CLINAME = "generate-tc-config"

    def __init__(
        self,
        output_file: str = ".taskcat.yml",
        main_template: str = "./templates/template.yaml",
        user_email: str = "noreply@acme.com",
        project_root: str = "./",
        aws_region: str = "us-east-1",
        verbose_config: bool = False,
        create_overrides_file: bool = True
    ):

        project_root_path = Path(project_root).expanduser().resolve()
        TaskCatConfigGenerator(main_template=main_template,
                               output_file=output_file,
                               project_root_path=str(project_root_path),
                               owner_email=user_email,
                               aws_region=aws_region,
                               verbose_config=verbose_config,
                               create_overrides_file=create_overrides_file).generate_config()
