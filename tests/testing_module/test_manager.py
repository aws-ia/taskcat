import os
import unittest
import uuid
from pathlib import Path

import yaml

from mock import MagicMock, patch
from taskcat import Config
from taskcat.testing.base_test import BaseTest
from taskcat.testing.cfn_test import CFNTest
from taskcat.testing.manager import TestManager


class TestTestManager(unittest.TestCase):
    def setUp(self):

        input_file = ".taskcat.yml"
        project_root_path = Path(__file__).parent / "../data/nested-fail"
        input_file_path = project_root_path / input_file

        self.base_config = Config.create(
            project_root=project_root_path, project_config_path=input_file_path,
        )

    @patch("taskcat.testing.manager.Config", autospec=True)
    def test_from_file(self, mock_config: MagicMock):
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
    def test_from_dict(self, mock_config: MagicMock):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()
        input_path = base_path / ".taskcat.yml"

        mock_config.return_value.uid = "test"

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

    def test_build_args(self):
        pass

    def test_init(self):
        test_manager = TestManager(self.base_config)

        self.assertIs(test_manager.config, self.base_config)
        self.assertIs(test_manager.printer, None)

        for test in test_manager.tests:
            self.assertIsInstance(test, BaseTest)

    @patch.object(TestManager, "start")
    @patch.object(TestManager, "end")
    def test_context(self, mock_start: MagicMock, mock_end: MagicMock):

        try:
            with TestManager(self.base_config) as test_manager:
                self.assertIsInstance(test_manager, TestManager)
        except BaseException:
            pass

        mock_start.assert_called()
        mock_end.assert_called()

    def test_set_tests(self):

        custom_test = [MagicMock()]

        test_manager = TestManager(self.base_config, tests=custom_test)

        self.assertEqual(custom_test, test_manager.tests)

    def test_start(self):
        mock_test = MagicMock()

        test_manager = TestManager(self.base_config)
        test_manager.tests = [mock_test]

        test_manager.start()

        mock_test.run.assert_called_once()

    def test_end(self):
        mock_test = MagicMock()

        test_manager = TestManager(self.base_config)
        test_manager.tests = [mock_test]

        test_manager.end()

        mock_test.clean_up.assert_called_once()

    def test_update_tests(self):
        cfn_test = CFNTest(self.base_config)
        tests = [MagicMock(), cfn_test, MagicMock()]
        test_manager = TestManager(self.base_config, tests=tests)

        updated_test = CFNTest(self.base_config, skip_upload=True)

        test_manager.update_tests([updated_test])

        self.assertIs(
            test_manager.tests[1],
            updated_test,
            "New Test should be inserted into correct locaton.",
        )

    def test_get_result(self):

        cfn_test = CFNTest(self.base_config)

        cfn_test.result = True

        test_manager = TestManager(self.base_config, tests=[cfn_test])

        result = test_manager.get_result("CFNTest")

        self.assertTrue(result, "Should return test result")
