import unittest
from pathlib import Path

from taskcat import Config
from taskcat.testing._lint_test import LintTest
from taskcat.testing.base_test import BaseTest


class TestLintTest(unittest.TestCase):

    BaseTest.__abstractmethods__ = set()

    @classmethod
    def setUpClass(cls):
        input_file = ".taskcat.yml"
        project_root_path = Path(__file__).parent / "../data/nested-fail"
        input_file_path = project_root_path / input_file

        cls.base_config = Config.create(
            project_root=project_root_path, project_config_path=input_file_path,
        )

    def test_methods(self):
        test = LintTest(self.base_config)

        with self.assertRaises(NotImplementedError):
            test.run()

        with self.assertRaises(NotImplementedError):
            test.clean_up()

    def test_inheritance(self):
        test = LintTest(self.base_config)

        self.assertIsInstance(test, BaseTest)
