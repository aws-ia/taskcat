from __future__ import print_function

import unittest

from taskcat.exceptions import TaskCatException
from taskcat.common_utils import param_list_to_dict


class TestCfnLogTools(unittest.TestCase):

    def test_get_param_includes(self):
        bad_testcases = [
            {},
            [[]],
            [{}]
        ]
        for bad in bad_testcases:
            with self.assertRaises(TaskCatException):
                param_list_to_dict(bad)
