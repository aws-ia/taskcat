import uuid
from pathlib import Path
from typing import Any, Dict, List, Union

from taskcat._cli_core import GLOBAL_ARGS
from taskcat._config import Config
from taskcat._tui import TerminalPrinter

from .ab_test import Test
from .cfn_test import CFNTest

Tests = List[Test]


class TestManager:
    """Manages the lifecycle of different kinds of Tests. All Tests
    must implement a run and clean_up method. They must also take a Config and
    Printer objects. See the Abstract Class Test for more info.
    """

    def __init__(
        self,
        config: Config,
        printer: Union[TerminalPrinter, None] = None,
        tests: Union[Tests, None] = None,
    ):
        self.config = config
        self.printer = printer

        # The defaults in the future will be Lint, Unit, CfnTest in that order.
        self.tests = tests if tests else [CFNTest(config, printer)]

    def __enter__(self):

        try:
            self.start()
        except BaseException as ex:
            self.end()
            raise ex

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    @classmethod
    def from_file(
        cls,
        project_root: str = "./",
        input_file: str = "./.taskcat.yml",
        regions: str = "ALL",
        enable_sig_v2: bool = False,
    ):
        """
        Creates a TestManger using a Taskcat config file.

        :param project_root: root path of the project relative to input_file
        :param input_file: path to a taskcat config file
        """
        project_root_path: Path = Path(project_root).expanduser().resolve()
        input_file_path: Path = project_root_path / input_file
        # pylint: disable=too-many-arguments
        args = _build_args(enable_sig_v2, regions, GLOBAL_ARGS.profile)
        config = Config.create(
            project_root=project_root_path,
            project_config_path=input_file_path,
            args=args
            # TODO: detect if input file is taskcat config or CloudFormation template
        )

        return cls(config)

    @classmethod
    def from_dict(
        cls,
        input_config: dict,
        project_root: str = "./",
        regions: str = "ALL",
        enable_sig_v2: bool = False,
    ):
        """
        Creates a TestManger using a Taskcat config file.

        :param project_root: root path of the project relative to input_file
        :param input_file: path to a taskcat config file
        """
        project_root_path: Path = Path(project_root).expanduser().resolve()

        # pylint: disable=too-many-arguments
        args = _build_args(enable_sig_v2, regions, GLOBAL_ARGS.profile)

        sources = [
            {"source": "Manual", "config": input_config},
            {"source": "CliArgument", "config": args},
        ]

        config = Config(
            uid=uuid.uuid4(), project_root=project_root_path, sources=sources
        )

        return cls(config)

    def start(self):
        """Calls the run method of the configured tests.
        """

        for test in self.tests:
            test.run()

    def end(self):
        """Calls the clean_up method on all configured tests.
        """

        for test in self.tests:
            test.clean_up()

    def update_tests(self, tests: Tests) -> None:
        new_tests: Tests = []

        # This may have not been the best way to do this
        # but its important that the list of tests maintain their order.
        for i in range(len(self.tests)):
            match = False
            for test in tests:
                # Mypy unable to understand `type(self.tests[i]) is type(test)`
                if type(self.tests[i]) is type(test):
                    new_tests.append(test)
                    match = True
                    break
            if not match:
                new_tests.append(self.tests[i])

        self.tests = new_tests

    def get_result(self, test_name: str) -> Any:
        for test in self.tests:
            if type(test).__name__ == test_name:
                return test.result
        # Not sure if we should return or throw exception
        return None


def _build_args(enable_sig_v2, regions, default_profile):
    args: Dict[str, Any] = {}
    if enable_sig_v2:
        args["project"] = {"s3_enable_sig_v2": enable_sig_v2}
    if regions != "ALL":
        if "project" not in args:
            args["project"] = {}
        args["project"]["regions"] = regions.split(",")
    if default_profile:
        _auth_dict = {"default": default_profile}
        if not args.get("project"):
            args["project"] = {"auth": _auth_dict}
        else:
            args["project"]["auth"] = _auth_dict
    return args
