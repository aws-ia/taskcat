import unittest
from pathlib import Path

from mock import ANY, MagicMock, Mock, patch
from taskcat import Config
from taskcat._tui import TerminalPrinter
from taskcat.exceptions import TaskCatException
from taskcat.testing import CFNTest

# Save some typing
m = Mock
mm = MagicMock


class TestCFNTest(unittest.TestCase):
    def setUp(self):

        input_file = ".taskcat.yml"
        project_root_path = Path(__file__).parent / "../data/nested-fail"
        input_file_path = project_root_path / input_file

        self.base_config = Config.create(
            project_root=project_root_path,
            project_config_path=input_file_path,
        )

    def test_init(self):

        # Test that parent constructor is called
        with patch("taskcat.testing.base_test.BaseTest.__init__") as mock_base:
            CFNTest(self.base_config)
            self.assertTrue(mock_base.called, "Parent Constructor must be called.")

        cfn_test = CFNTest(self.base_config)

        default_attr = {
            "test_names": "ALL",
            "regions": "ALL",
            "skip_upload": False,
            "lint_disable": False,
            "no_delete": False,
            "keep_failed": False,
            "dont_wait_for_delete": True,
        }

        self.assertDictContainsSubset(
            default_attr,
            cfn_test.__dict__,
            "Make sure default values are not accidentally changed.",
        )

        self.assertFalse(
            hasattr(cfn_test, "test_definition"), "Should not set test_definition."
        )
        self.assertIsInstance(
            cfn_test.printer,
            TerminalPrinter,
            "Should create a TerminalPrinter if none passed in.",
        )

    def test_set_printer(self):

        mock_printer = MagicMock()

        cfn_test = CFNTest(self.base_config, mock_printer)

        self.assertEqual(cfn_test.printer, mock_printer, "Should use our printer.")

    @patch("taskcat.testing._cfn_test.Stacker", autospec=True)
    @patch("taskcat.testing._cfn_test.stage_in_s3", autospec=True)
    @patch("taskcat.testing._cfn_test.LambdaBuild", autospec=True)
    def test_run(self, mock_lambda: mm, mock_stage_s3: mm, mock_stacker: mm):

        stacker = mock_stacker.return_value

        stacker.stacks = []

        cfn_test = CFNTest(self.base_config)

        # Create all the config mocks
        mock_get_buckets: m = Mock()
        mock_get_regions: m = Mock()
        mock_get_parameters: m = Mock()
        mock_get_tests: m = Mock()
        mock_printer: m = Mock()

        # Assign all the config mocks
        cfn_test.config.get_buckets = mock_get_buckets
        cfn_test.config.get_regions = mock_get_regions
        cfn_test.config.get_rendered_parameters = mock_get_parameters
        cfn_test.config.get_tests = mock_get_tests
        cfn_test.printer = mock_printer

        cfn_test.run()

        # Test all the mocks
        mock_get_buckets.assert_called_once()
        mock_lambda.assert_called_once_with(
            cfn_test.config, cfn_test.config.project_root
        )
        mock_stage_s3.assert_called_once_with(
            mock_get_buckets.return_value,
            cfn_test.config.config.project.name,
            cfn_test.config.project_root,
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
            cfn_test.config.config.project.name,
            mock_get_tests.return_value,
            shorten_stack_name=cfn_test.config.config.project.shorten_stack_name,
        )
        mock_stacker.return_value.create_stacks.assert_called_once()
        mock_printer.report_test_progress.assert_called_once_with(
            stacker=cfn_test.test_definition
        )

        self.assertTrue(cfn_test.passed, "Should set passed after a successful deploy.")
        self.assertIsInstance(
            cfn_test.result, list, "Should set result to a list of stacks."
        )

    def test_run_failure(self):
        # We should test what happens when a stack fails.
        # Right now the current behavior is to just throw an exception
        # but maybe we should catch it, set passed to False and result
        # to some information, like the error
        pass

    @patch("taskcat.testing._cfn_test.Stacker", autospec=True)
    @patch("taskcat.testing._cfn_test.stage_in_s3", autospec=True)
    @patch("taskcat.testing._cfn_test.Config")
    def test_skip_upload(self, mock_config: mm, mock_stage_s3: mm, mock_stacker: mm):

        stacker = mock_stacker.return_value

        stacker.stacks = []

        cfn_test = CFNTest(mock_config(), skip_upload=True)

        config_obj = mock_config.return_value

        config_obj.config.project.s3_bucket = ""

        # Should fail if we don't specify an existing s3 bucket
        with self.assertRaises(TaskCatException) as ex:
            cfn_test.run()

        self.assertEqual(
            str(ex.exception),
            "cannot skip_buckets without specifying s3_bucket in config",
        )

        cfn_test.config.config.project.s3_bucket = "FakeBucket"

        cfn_test.run()

        # Test all the mocks
        self.assertFalse(mock_stage_s3.called, "Should not stage in s3.")

    @patch("taskcat.testing._cfn_test.Stacker", autospec=True)
    @patch("taskcat.testing._cfn_test.stage_in_s3", autospec=True)
    @patch("taskcat.testing._cfn_test.Config")
    @patch("taskcat.testing._cfn_test.TaskCatLint", autospec=True)
    def test_lint(
        self, mock_lint: mm, mock_config: mm, mock_stage_s3: mm, mock_stacker: mm
    ):

        stacker = mock_stacker.return_value

        stacker.stacks = []

        cfn_test = CFNTest(mock_config(), lint_disable=True)

        config_obj = mock_config.return_value
        config_obj.config.project.s3_bucket = ""
        config_obj.config.project.package_lambda = False
        lint_obj = mock_lint.return_value
        lint_obj.lints = [False, False]
        lint_obj.passed = True

        cfn_test.run()

        lint_obj.output_results.assert_not_called()

        cfn_test.lint_disable = False

        cfn_test.run()

        lint_obj.output_results.assert_called_once()

        lint_obj.passed = False

        # Should fail if we don't specify an existing s3 bucket
        with self.assertRaises(TaskCatException) as ex:
            cfn_test.run()

        self.assertEqual(str(ex.exception), "Lint failed with errors")

    @patch("taskcat.testing._cfn_test.Config")
    def test_clean_up(self, mock_config: mm):
        cfn_test = CFNTest(mock_config())

        # Clean up when stacks failed to create
        cfn_test.clean_up()

        td_mock = MagicMock()

        cfn_test.test_definition = td_mock

        # Clean up after stacks have created
        cfn_test.clean_up()

        td_mock.status.assert_called()
        td_mock.delete_stacks.assert_called_once()

    @patch("taskcat.testing._cfn_test.Config")
    def test_end_no_delete(self, mock_config: mm):
        cfn_test = CFNTest(mock_config(), no_delete=True)

        td_mock: mm = MagicMock()

        cfn_test.test_definition = td_mock

        cfn_test.clean_up()

        td_mock.delete_stacks.assert_not_called()

    @patch("taskcat.testing._cfn_test.Config")
    def test_end_keep_failed(self, mock_config: mm):
        cfn_test = CFNTest(mock_config(), keep_failed=True)

        td_mock = MagicMock()
        td_mock.status.return_value = {"COMPLETE": [1], "FAILED": []}

        cfn_test.test_definition = td_mock

        cfn_test.clean_up()

        td_mock.delete_stacks.assert_called_once_with({"status": "CREATE_COMPLETE"})

        td_mock.status.return_value = {"COMPLETE": [1], "FAILED": [1]}

        # Should fail if a stack fails.
        with self.assertRaises(TaskCatException) as ex:
            cfn_test.clean_up()

        self.assertTrue("One or more stacks failed to create:" in str(ex.exception))

    @patch("taskcat.testing._cfn_test.Config")
    @patch("taskcat.testing._cfn_test._CfnLogTools")
    @patch("taskcat.testing._cfn_test.ReportBuilder")
    def test_report(self, mock_report: mm, mock_log: mm, mock_config: mm):
        cfn_test = CFNTest(mock_config())

        td_mock = MagicMock()

        cfn_test.test_definition = td_mock

        cfn_test.report()

        mock_log.return_value.createcfnlogs.assert_called_once()
        mock_report.return_value.generate_report.assert_called_once()

    def test_trim_regions(self):
        pass

    def test_trim_tests(self):
        pass
