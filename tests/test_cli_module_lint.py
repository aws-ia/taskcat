import os
import unittest
from pathlib import Path

from taskcat._cli_modules.lint import Lint


class TestLintCli(unittest.TestCase):
    def test_lint(self):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/nested-fail").resolve()
        Lint(project_root=base_path, input_file=base_path / ".taskcat.yml")
        # nothing to assert, expected to return nothing and exit without error
