import os
import unittest
from pathlib import Path

import mock

from taskcat._cli_modules.lint import Lint


class TestNewConfig(unittest.TestCase):
    @mock.patch("taskcat._cli_modules.lint.Boto3Cache", autospec=True)
    def test_lint(self, _):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()
        Lint(project_root=base_path, input_file=base_path / ".taskcat.yml")
        # nothing to assert, expected to return nothing and exit without error
