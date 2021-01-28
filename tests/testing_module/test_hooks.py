import unittest
from pathlib import Path

from mock import MagicMock, patch
from taskcat import Config
from taskcat.exceptions import TaskCatException
from taskcat.testing import CFNTest


class TestCFNTest(unittest.TestCase):
    def setUp(self):
        self.project_root_path = Path(__file__).parent / "../data/hook_plugin"
        self.input_file_path = self.project_root_path / ".taskcat.yml"

    @patch("taskcat.testing._cfn_test.Stacker")
    def test_execute_hooks_fail(self, mock_stacker: MagicMock):
        mock_stacker.stacks.return_value = None
        config = Config.create(
            project_root=self.project_root_path,
            project_config_path=self.input_file_path,
        )

        t = CFNTest(config, lint_disable=True, test_names="hook-fail")
        with self.assertRaises(TaskCatException) as exc:
            t.run()
        self.assertEqual(
            str(exc.exception),
            "One or more hooks failed [('testhook', 'hook-fail', 'generated failure from hook')]",
        )

    @patch("taskcat.testing._cfn_test.Stacker")
    def test_execute_hooks_pass(self, mock_stacker: MagicMock):
        mock_stacker.stacks.return_value = None
        config = Config.create(
            project_root=self.project_root_path,
            project_config_path=self.input_file_path,
        )
        t = CFNTest(config, lint_disable=True, test_names="hook-pass")
        t.run()
        self.assertEqual(t.passed, True)

    @patch("taskcat.testing._cfn_test.Stacker")
    def test_execute_hooks_nonexistant(self, mock_stacker: MagicMock):
        mock_stacker.stacks.return_value = None
        config = Config.create(
            project_root=self.project_root_path,
            project_config_path=self.input_file_path,
        )
        t = CFNTest(config, lint_disable=True, test_names="hook-nonexist")
        with self.assertRaises(TaskCatException) as exc:
            t.run()
        self.assertEqual(str(exc.exception), 'hook "testhookthatdoesntexist" not found')
