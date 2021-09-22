import unittest
from unittest import mock

from taskcat import _cli_modules
from taskcat._cli_core import GLOBAL_ARGS, CliCore


class TestCliCore(unittest.TestCase):
    def test_cli_core(self):
        cli = CliCore(
            "taskcat-test", _cli_modules, "test description", "0.1", GLOBAL_ARGS.ARGS
        )
        self.assertIn("lint", cli._modules)
        self.assertIn("package", cli._modules)
        self.assertIn("test", cli._modules)
        self.assertCountEqual(["-q", "--quiet"], cli.parser._actions[2].option_strings)
        self.assertCountEqual(["-d", "--debug"], cli.parser._actions[3].option_strings)
        self.assertCountEqual(
            ["-v", "--version"], cli.parser._actions[1].option_strings
        )

    def test_parse(self):
        cli = CliCore(
            "taskcat-test", _cli_modules, "test description", "0.1", GLOBAL_ARGS.ARGS
        )
        cli.parser.parse_args = mock.Mock()
        actual = cli.parse()
        self.assertIsInstance(actual, mock.Mock)

    def test_run(self):
        cli = CliCore(
            "taskcat-test", _cli_modules, "test description", "0.1", GLOBAL_ARGS.ARGS
        )
        cli._modules["lint"] = mock.Mock()
        cli.parse(["lint", "-i", "test-taskcat.yml", "-p", "./"])
        actual = cli.run()
        self.assertIsInstance(actual, mock.Mock)
