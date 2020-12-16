import unittest
from pathlib import Path
from unittest.mock import DEFAULT, patch

import yaml

from taskcat import Config
from taskcat.testing.ab_test import Test
from taskcat.testing.base_test import BaseTest


class TestBaseTest(unittest.TestCase):

    BaseTest.__abstractmethods__ = set()
    Test.__abstractmethods__ = set()

    @classmethod
    def setUpClass(cls):
        cls.input_file = ".taskcat.yml"
        cls.project_root_path = Path(__file__).parent / "../data/nested-fail"
        cls.input_file_path = cls.project_root_path / cls.input_file

        cls.base_config = Config.create(
            project_root=cls.project_root_path, project_config_path=cls.input_file_path,
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

    def test_from_file(self):

        base = BaseTest.from_file(project_root=self.project_root_path)

        self.assertIsInstance(base, BaseTest, "Should return an instance of BaseTest.")

        self.assertIsInstance(base.config, Config)

    def test_from_dict(self):

        with open(self.input_file_path) as f:
            test_config = yaml.load(f, Loader=yaml.FullLoader)

        base = BaseTest.from_dict(test_config, project_root=self.project_root_path)

        self.assertIsInstance(base, BaseTest, "Should return an instance of BaseTest.")

        self.assertIsInstance(base.config, Config)
