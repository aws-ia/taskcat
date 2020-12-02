import os
import unittest
import uuid
from pathlib import Path

import yaml

import mock
from taskcat._tui import TerminalPrinter
from taskcat.testing import TestManager


class TestTestManager(unittest.TestCase):
    @mock.patch("taskcat.testing.manager.Config", autospec=True)
    def test_from_file(self, mock_config):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()
        input_path = base_path / ".taskcat.yml"

        test_manager = TestManager.from_file(str(base_path))

        self.assertIsInstance(
            test_manager, TestManager, "Should return an instance of TestManager."
        )

        _, kwargs = mock_config.create.call_args_list[0]

        default_args = {"project": {"auth": {"default": "default"}}}
        self.assertIsInstance(kwargs["args"], dict, "Should pass a dictionary to args.")
        self.assertDictEqual(
            kwargs["args"], default_args, "Should pass in these defaults."
        )

        self.assertIsInstance(
            kwargs["project_root"], Path, "Should pass in a Path object."
        )
        self.assertEqual(
            kwargs["project_root"], base_path, "Should turn our str into a Path."
        )

        self.assertIsInstance(
            kwargs["project_config_path"], Path, "Should pass in a Path object."
        )
        self.assertEqual(
            kwargs["project_config_path"],
            input_path,
            "Should turn our str into a Path.",
        )

    @mock.patch("taskcat.testing.manager.Config", autospec=True)
    def test_from_dict(self, mock_config):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()
        input_path = base_path / ".taskcat.yml"

        with open(str(input_path)) as f:
            test_config = yaml.load(f, Loader=yaml.FullLoader)

        test_manager = TestManager.from_dict(test_config, project_root=str(base_path))

        self.assertIsInstance(
            test_manager, TestManager, "Should return an instance of TestManager."
        )

        _, kwargs = mock_config.call_args_list[0]

        self.assertIsInstance(kwargs["uid"], uuid.UUID, "Should pass a uid.")
        self.assertIsNotNone(kwargs["uid"], "Should set a value.")

        self.assertIsInstance(
            kwargs["project_root"], Path, "Should pass in a Path object."
        )
        self.assertEqual(
            kwargs["project_root"], base_path, "Should turn our str into a Path."
        )

        self.assertIsInstance(kwargs["sources"], list, "Should pass in a list.")

        for item in kwargs["sources"]:
            self.assertIsInstance(item, dict, "Should be a dictionary")
            self.assertTrue("config" in item, "Should contain config key.")
            self.assertTrue("source" in item, "Should contain source key.")

    @mock.patch("taskcat.testing.manager.Config", autospec=True)
    def test_default(self, mock_config):

        test_manager = TestManager(mock_config)

        self.assertEqual(
            test_manager.config, mock_config, "Should set our config property."
        )
        self.assertFalse(
            hasattr(test_manager, "test_definition"), "Should not set test_definition."
        )
        self.assertIsInstance(
            test_manager.printer,
            TerminalPrinter,
            "Should create a TerminalPrinter if none passed in.",
        )

    @mock.patch("taskcat.testing.manager.Config", autospec=True)
    def test_printer_overide(self, mock_config):

        mock_printer = mock.MagicMock()

        test_manager = TestManager(mock_config, mock_printer)

        self.assertEqual(test_manager.printer, mock_printer, "Should use our printer.")
