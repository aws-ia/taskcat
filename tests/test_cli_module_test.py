import os
import unittest
from pathlib import Path
from unittest import mock

from taskcat._cli_modules.test import Test


class TestTestCli(unittest.TestCase):
    @mock.patch("taskcat._cli_modules.test.CFNTest", autospec=True)
    def test_test_run(self, mock_test):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()
        input_path = base_path / ".taskcat.yml"

        Test.run(project_root=base_path, input_file=input_path)

        # Make sure we created test_manager using from_file
        mock_test.from_file.assert_called_once_with(base_path, input_path, "ALL", False)

        # Mock test is the class, here we get an instance of it
        test = mock_test.from_file.return_value

        test.__enter__.assert_called_once()
        test.report.assert_called_once_with("./taskcat_outputs")
        test.__exit__.assert_called_once()

    @mock.patch("taskcat._cli_modules.test.Config", autospec=True)
    @mock.patch("taskcat._cli_modules.test.Test", autospec=True)
    @mock.patch("taskcat._cli_modules.test.boto3.Session", autospec=True)
    def test_test_retry(self, mock_boto_session, mock_test, mock_config):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()
        mock_client = mock.MagicMock()
        mock_describe = mock.MagicMock()
        mock_describe.return_value = {
            "StackEvents": [
                {
                    "PhysicalResourceId": "pid",
                    "LogicalResourceId": "MyResource",
                    "ResourceProperties": '{"Parameters": [], "TemplateURL": '
                    '"https://some/url"}',
                }
            ]
        }
        mock_client.return_value.describe_stack_events = mock_describe
        mock_boto_session.return_value.client = mock_client
        Test.retry(
            project_root=base_path,
            config_file=base_path / ".taskcat.yml",
            region="us-east-1",
            stack_name="test-stack",
            resource_name="MyResource",
        )
        mock_config.create.assert_called()
        mock_test.run.assert_called()
