from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from taskcat._config import Config

T = TypeVar("T", bound="Test")  # pylint: disable=invalid-name


class Test(ABC):
    """Abstract Test class the forces subclasses to implement
    a run method to be called to start a test run and a clean_up
    method to be called afterwards. All subclasses must have a
    config, passed and result property.
    """

    @property  # type: ignore
    @abstractmethod
    def config(self) -> Config:
        """Get or set the current Test configuration.
        """

    @config.setter  # type: ignore
    @abstractmethod
    def config(self, config: Config) -> None:
        pass

    @property  # type: ignore
    @abstractmethod
    def passed(self) -> bool:
        """Get the result of the current test. Defaults to False if test hasn't run.
        """

    @passed.setter  # type: ignore
    @abstractmethod
    def passed(self, new_value: bool) -> None:
        pass

    @property  # type: ignore
    @abstractmethod
    def result(self) -> Any:
        """Get the result of the Test. Defaults to None if test hasn't run.
        """

    @result.setter  # type: ignore
    @abstractmethod
    def result(self, new_value: Any) -> None:
        pass

    @abstractmethod
    def __enter__(self) -> Any:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        """Run the Test."""

    @abstractmethod
    def clean_up(self) -> None:
        """Clean up after the Test."""

    @classmethod
    def from_file(
        cls: Type[T],
        project_root: str,
        input_file: str,
        regions: str,
        enable_sig_v2: bool,
    ) -> T:
        pass

    @classmethod
    @abstractmethod
    def from_dict(
        cls: Type[T],
        input_config: dict,
        project_root: str,
        regions: str,
        enable_sig_v2: bool,
    ) -> T:
        pass
