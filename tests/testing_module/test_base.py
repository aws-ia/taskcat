import unittest
from pathlib import Path
from unittest.mock import DEFAULT, patch

from taskcat import Config
from taskcat.testing.ab_test import Test
from taskcat.testing.base_test import BaseTest


class TestBaseTest(unittest.TestCase):

    BaseTest.__abstractmethods__ = set()
    Test.__abstractmethods__ = set()

    @classmethod
    def setUpClass(cls):
        input_file = ".taskcat.yml"
        project_root_path = Path(__file__).parent / "../data/nested-fail"
        input_file_path = project_root_path / input_file

        cls.base_config = Config.create(
            project_root=project_root_path, project_config_path=input_file_path,
        )

    def test_init(self):
        base = BaseTest(self.base_config)

        self.assertIs(base.config, self.base_config, "Should set config property.")

        self.assertFalse(base.passed, "Should start with a default of False.")
        self.assertIsNone(base.result, "Should start with no result.")

        base.passed = True
        base.result = []

        self.assertTrue(base.passed, "Should set passed property.")
        self.assertIsInstance(base.result, list, "Should set result property.")

    def test_context(self):
        base = BaseTest(self.base_config)

        with patch.multiple(base, run=DEFAULT, clean_up=DEFAULT) as mocks:
            with base as result:
                self.assertIsNone(result)

            mocks["run"].assert_called()
            mocks["clean_up"].assert_called()

    def test_inheritance(self):
        base = BaseTest(self.base_config)

        self.assertIsInstance(base, Test)
