from taskcat._config import Config

from .base_test import BaseTest


class UnitTest(BaseTest):
    """UnitTest Cloudformation locally without deploying them to AWS.
    """

    def __init__(self, config: Config):  # pylint: disable=W0235
        """Creates a Test from an existing Config object.

        Args:
            config (Config): A pre-configured Taskcat Config instance.
        """
        super().__init__(config)

    def run(self):  # pylint: disable=W0221
        """Renders out any AWS Variables or Conditionals from the Test templates.

        Raises:
            NotImplementedError: Thrown until this class is implemented.
        """
        raise NotImplementedError

    def clean_up(self):  # pylint: disable=W0221
        """Cleans up after the Test.

        Raises:
            NotImplementedError: Thrown until this class is implemented.
        """
        raise NotImplementedError
