import logging
from taskcat.config import Config
from taskcat.exceptions import TaskCatException
from taskcat.cfn_lint import Lint as TaskCatLint

LOG = logging.getLogger(__name__)


class Lint:
    def __init__(self, input_file: str, project_root: str = './', strict: bool = False):
        try:
            config = Config(template_path=input_file, project_root=project_root)
        except Exception as e:
            LOG.debug(e.__class__.__name__)
            LOG.debug(e, exc_info=True)
            config = Config(project_config_path=input_file, project_root=project_root)
        lint, errors = TaskCatLint(config, strict)
        lint.output_results()
        if errors or not lint.passed:
            raise TaskCatException("Lint failed with errors")
