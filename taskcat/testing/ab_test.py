import uuid
from abc import ABC, abstractmethod


class Test(ABC):
    """Abstract Test class the forces subclasses to implement
    a run method to be called to start a test run and optionally
    a clean_up method to be called afterwards. All subclasses must
    have a uid and passed property.
    """

    @property  # type: ignore
    @abstractmethod
    def uid(self):
        pass

    @uid.setter  # type: ignore
    @abstractmethod
    def uid(self, uid: uuid.UUID):
        pass

    @property  # type: ignore
    @abstractmethod
    def passed(self):
        pass

    @passed.setter  # type: ignore
    @abstractmethod
    def passed(self, passed: bool):
        pass

    @abstractmethod
    def run(self):
        """Run the Test."""

    @abstractmethod
    def clean_up(self, *args, **kwargs):
        """Clean up the Test."""
