import os
import unittest
from pathlib import Path

import mock
from taskcat._cli_modules.test import Test


class TestTestCli(unittest.TestCase):
    @mock.patch("taskcat._cli_modules.test.Config", autospec=True)
    @mock.patch("taskcat._cli_modules.test.LambdaBuild", autospec=True)
    @mock.patch("taskcat._cli_modules.test.ReportBuilder", autospec=True)
    def test_test_run(self, mock_report_builder, mock_lambda_build, mock_config):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()

        Test.run(project_root=base_path, input_file=base_path / ".taskcat.yml")
        mock_report_builder.assert_called()
        mock_lambda_build.assert_called()
        mock_config.create.assert_called()
