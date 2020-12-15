from typing import Any

from taskcat._config import Config
from taskcat.testing.ab_test import Test


class BaseTest(Test):
    """A Generic Test Class that implements the passed
    and uid properties. Any subclass will still need to
    implement the the run and clean_up methods.
    """

    def __init__(self, config: Config):
        self.config: Config = config
        self.passed: bool = False
        self.result: Any = None

    @property
    def config(self) -> Config:
        return self._config

    @config.setter
    def config(self, config: Config) -> None:
        # It should be possible to check if config is already set
        # and if it is throw an exception. Might be needed since
        # child objects rely on the configs uid.
        self._config = config

    @property
    def passed(self) -> bool:
        return self._passed

    @passed.setter
    def passed(self, new_value: bool) -> None:
        self._passed = new_value

    @property
    def result(self) -> Any:
        return self._result

    @result.setter
    def result(self, new_value: Any) -> None:
        self._result = new_value
