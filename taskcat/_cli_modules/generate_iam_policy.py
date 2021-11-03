import logging
from pathlib import Path

from taskcat._config import Config
from taskcat.iam_policy.policy import CFNPolicyGenerator

LOG = logging.getLogger(__name__)


class GenerateIAMPolicy:
    """
    [ALPHA] Introspects CFN Template(s) and generates an IAM policy necessary to successfully launch the template(s)
    """

    CLINAME = "generate-iam-policy"

    def __init__(
        self, output_file: str = "./cfn_stack_policy.json", project_root: str = "./"
    ):
        project_root_path = Path(project_root).expanduser().resolve()

        config = Config.create(project_root=project_root_path)

        CFNPolicyGenerator(config, output_file).generate_policy()
