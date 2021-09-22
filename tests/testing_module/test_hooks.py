import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from taskcat import Config
from taskcat.exceptions import TaskCatException
from taskcat.testing import CFNTest


def get_config():
    project_root_path = Path(__file__).parent / "../data/hook_plugin"
    input_file_path = project_root_path / ".taskcat.yml"
    config = Config.create(
        project_root=project_root_path,
        project_config_path=input_file_path,
    )
    config.get_buckets = MagicMock()
    config.get_regions = MagicMock()
    config.get_rendered_parameters = MagicMock()
    config.get_tests = MagicMock()
    return config


class TestHooks(unittest.TestCase):
    @patch("taskcat.testing._cfn_test.Stacker")
    @patch("taskcat.testing._cfn_test.Boto3Cache", autospec=True)
    def test_execute_hooks_fail(self, _m_s: MagicMock, _m_bc: MagicMock):
        config = get_config()
        t = CFNTest(config, lint_disable=True, skip_upload=True, test_names="hook-fail")
        with self.assertRaises(TaskCatException) as exc:
            t.run()
        self.assertEqual(
            str(exc.exception),
            "One or more hooks failed [('testhook', 'hook-fail', 'generated failure from hook')]",
        )

    @patch("taskcat.testing._cfn_test.Stacker")
    @patch("taskcat.testing._cfn_test.Boto3Cache")
    def test_execute_hooks_pass(self, _m_s: MagicMock, _m_bc: MagicMock):
        config = get_config()
        t = CFNTest(config, lint_disable=True, skip_upload=True, test_names="hook-pass")
        t.run()
        self.assertEqual(t.passed, True)

    @patch("taskcat.testing._cfn_test.Stacker")
    @patch("taskcat.testing._cfn_test.Boto3Cache")
    def test_execute_hooks_nonexistant(self, _m_s: MagicMock, _m_bc: MagicMock):
        config = get_config()
        t = CFNTest(
            config, lint_disable=True, skip_upload=True, test_names="hook-nonexist"
        )
        with self.assertRaises(TaskCatException) as exc:
            t.run()
        self.assertEqual(str(exc.exception), 'hook "testhookthatdoesntexist" not found')
