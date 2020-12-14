import uuid
from typing import Union

from .ab_test import Test


class BaseTest(Test):
    """A Generic Test Class that implements the passed
    and uid properties. Any subclass will still need to
    implement the the run and clean_up methods.
    """

    def __init__(self, uid: Union[uuid.UUID, None] = None):
        self.uid = uid if uid else uuid.uuid4()
        self.passed = False

    @property
    def uid(self) -> uuid.UUID:
        return self._uid

    @uid.setter
    def uid(self, uid: uuid.UUID) -> None:
        self._uid = uid

    @property
    def passed(self) -> bool:
        return self._passed

    @passed.setter
    def passed(self, value: bool) -> None:
        self._passed = value
