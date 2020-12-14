import uuid
from typing import Union

from .base_test import BaseTest


class LintTest(BaseTest):
    def __init__(self, uid: Union[uuid.UUID, None] = None):  # pylint: disable=W0235
        super().__init__(uid)

    def run(self):  # pylint: disable=W0221
        raise NotImplementedError

    def clean_up(self):  # pylint: disable=W0221
        raise NotImplementedError
