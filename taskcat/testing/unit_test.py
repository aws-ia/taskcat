from taskcat._config import Config

from .base_test import BaseTest


class UnitTest(BaseTest):
    def __init__(self, config: Config):  # pylint: disable=W0235
        super().__init__(config)

    def run(self):  # pylint: disable=W0221
        raise NotImplementedError

    def clean_up(self):  # pylint: disable=W0221
        raise NotImplementedError
