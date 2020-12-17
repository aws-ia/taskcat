from taskcat._config import Config

from .base_test import BaseTest


class LintTest(BaseTest):
    """Lints Cloudformation Templates using cfn-lint. (Not yet implemented)
    """

    def __init__(self, config: Config):  # pylint: disable=W0235
        """Creates a Test from an existing Config object.

        Args:
            config (Config): A pre-configured Taskcat Config instance.
        """
        super().__init__(config)

    def run(self):
        """Runs cfn-lint againt the Test templates.

        Raises:
            NotImplementedError: Thrown until this class is implemented.
        """
        raise NotImplementedError

    def clean_up(self):
        """Cleans up cfn-lint Test resources.

        Raises:
            NotImplementedError: Thrown until this class is implemented.
        """
        raise NotImplementedError
