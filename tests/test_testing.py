import os
import unittest
import uuid
from pathlib import Path

import yaml

from mock import ANY, MagicMock, Mock, patch
from taskcat._tui import TerminalPrinter
from taskcat.exceptions import TaskCatException
from taskcat.testing import TestManager

# Save some typing
m = Mock
mm = MagicMock


class TestTestManager(unittest.TestCase):
    @patch("taskcat.testing.manager.Config", autospec=True)
    def test_from_file(self, mock_config: mm):
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

    @patch("taskcat.testing.manager.Config", autospec=True)
    def test_from_dict(self, mock_config: mm):
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

    @patch("taskcat.testing.manager.Config", autospec=True)
    def test_default(self, mock_config: mm):

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

    @patch("taskcat.testing.manager.Config", autospec=True)
    def test_printer_overide(self, mock_config: mm):

        mock_printer = MagicMock()

        test_manager = TestManager(mock_config, mock_printer)

        self.assertEqual(test_manager.printer, mock_printer, "Should use our printer.")

    @patch("taskcat.testing.manager.Stacker", autospec=True)
    @patch("taskcat.testing.manager.stage_in_s3", autospec=True)
    @patch("taskcat.testing.manager.LambdaBuild", autospec=True)
    def test_start_default(self, mock_lambda: mm, mock_stage_s3: mm, mock_stacker: mm):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()

        test_manager = TestManager.from_file(str(base_path))

        # Create all the config mocks
        mock_get_buckets: m = Mock()
        mock_get_regions: m = Mock()
        mock_get_parameters: m = Mock()
        mock_get_tests: m = Mock()
        mock_printer: m = Mock()

        # Assign all the config mocks
        test_manager.config.get_buckets = mock_get_buckets
        test_manager.config.get_regions = mock_get_regions
        test_manager.config.get_rendered_parameters = mock_get_parameters
        test_manager.config.get_tests = mock_get_tests
        test_manager.printer = mock_printer

        test_manager.start()

        # Test all the mocks
        mock_get_buckets.assert_called_once()
        mock_lambda.assert_called_once_with(test_manager.config, base_path)
        mock_stage_s3.assert_called_once_with(
            mock_get_buckets.return_value,
            test_manager.config.config.project.name,
            test_manager.config.project_root,
        )
        mock_get_regions.assert_called_once()
        mock_get_parameters.assert_called_once_with(
            mock_get_buckets.return_value, mock_get_regions.return_value, ANY
        )
        mock_get_tests.assert_called_once_with(
            ANY,
            mock_get_regions.return_value,
            mock_get_buckets.return_value,
            mock_get_parameters.return_value,
        )
        mock_stacker.assert_called_with(
            test_manager.config.config.project.name,
            mock_get_tests.return_value,
            shorten_stack_name=test_manager.config.config.project.shorten_stack_name,
        )
        mock_stacker.return_value.create_stacks.assert_called_once()
        mock_printer.report_test_progress.assert_called_once_with(
            stacker=test_manager.test_definition
        )

    @patch("taskcat.testing.manager.Stacker", autospec=True)
    @patch("taskcat.testing.manager.stage_in_s3", autospec=True)
    @patch("taskcat.testing.manager.Config")
    def test_start_skip_upload(
        self, mock_config: mm, mock_stage_s3: mm, mock_stacker: mm
    ):

        test_manager = TestManager(mock_config())

        config_obj = mock_config.return_value

        config_obj.config.project.s3_bucket = ""

        # Should fail if we don't specify an existing s3 bucket
        with self.assertRaises(TaskCatException) as ex:
            test_manager.start(skip_upload=True)

        self.assertEqual(
            str(ex.exception),
            "cannot skip_buckets without specifying s3_bucket in config",
        )

        test_manager.config.config.project.s3_bucket = "FakeBucket"

        test_manager.start(skip_upload=True)

        # Test all the mocks
        self.assertFalse(mock_stage_s3.called, "Should not stage in s3.")

    @patch("taskcat.testing.manager.Stacker", autospec=True)
    @patch("taskcat.testing.manager.stage_in_s3", autospec=True)
    @patch("taskcat.testing.manager.Config")
    @patch("taskcat.testing.manager.TaskCatLint", autospec=True)
    def test_start_lint(
        self, mock_lint: mm, mock_config: mm, mock_stage_s3: mm, mock_stacker: mm
    ):

        test_manager = TestManager(mock_config())

        config_obj = mock_config.return_value
        config_obj.config.project.s3_bucket = ""
        config_obj.config.project.package_lambda = False
        lint_obj = mock_lint.return_value
        lint_obj.lints = [False, False]
        lint_obj.passed = True

        test_manager.start(lint_disable=True)

        lint_obj.output_results.assert_not_called()

        test_manager.start()

        lint_obj.output_results.assert_called_once()

        lint_obj.passed = False

        # Should fail if we don't specify an existing s3 bucket
        with self.assertRaises(TaskCatException) as ex:
            test_manager.start()

        self.assertEqual(str(ex.exception), "Lint failed with errors")

    @patch("taskcat.testing.manager.Config")
    def test_end_default(self, mock_config: mm):
        test_manager = TestManager(mock_config())

        td_mock = MagicMock()

        test_manager.test_definition = td_mock

        test_manager.end()

        td_mock.status.assert_called()
        td_mock.delete_stacks.assert_called_once()

    @patch("taskcat.testing.manager.Config")
    def test_end_no_delete(self, mock_config: mm):
        test_manager = TestManager(mock_config())

        td_mock: mm = MagicMock()

        test_manager.test_definition = td_mock

        test_manager.end(no_delete=True)

        td_mock.delete_stacks.assert_not_called()

    @patch("taskcat.testing.manager.Config")
    def test_end_keep_failed(self, mock_config: mm):
        test_manager = TestManager(mock_config())

        td_mock = MagicMock()
        td_mock.status.return_value = {"COMPLETE": [1], "FAILED": []}

        test_manager.test_definition = td_mock

        test_manager.end(keep_failed=True)

        td_mock.delete_stacks.assert_called_once_with({"status": "CREATE_COMPLETE"})

        td_mock.status.return_value = {"COMPLETE": [1], "FAILED": [1]}

        # Should fail if a stack fails.
        with self.assertRaises(TaskCatException) as ex:
            test_manager.end(keep_failed=True)

        self.assertTrue("One or more stacks failed tests:" in str(ex.exception))

    @patch("taskcat.testing.manager.Config")
    @patch("taskcat.testing.manager._CfnLogTools")
    @patch("taskcat.testing.manager.ReportBuilder")
    def test_report(self, mock_report: mm, mock_log: mm, mock_config: mm):
        test_manager = TestManager(mock_config())

        td_mock = MagicMock()

        test_manager.test_definition = td_mock

        test_manager.report()

        mock_log.return_value.createcfnlogs.assert_called_once()
        mock_report.return_value.generate_report.assert_called_once()

    def test_trim_regions(self):
        pass

    def test_trim_tests(self):
        pass

    def test_build_args(self):
        pass
