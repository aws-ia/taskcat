import uuid
from pathlib import Path
from typing import Any, Dict

from taskcat._cli_core import GLOBAL_ARGS
from taskcat._config import Config

from .ab_test import Test


class BaseTest(Test):
    """A Generic Test Class that implements the passed
    and uid properties. Any subclass will still need to
    implement the the run and clean_up methods.
    """

    def __init__(self, config: Config):
        self.config: Config = config
        self.passed: bool = False
        self.result: Any = None

    @property
    def config(self) -> Config:
        return self._config

    @config.setter
    def config(self, config: Config) -> None:
        # It should be possible to check if config is already set
        # and if it is throw an exception. Might be needed since
        # child objects rely on the configs uid.
        self._config = config

    @property
    def passed(self) -> bool:
        return self._passed

    @passed.setter
    def passed(self, new_value: bool) -> None:
        self._passed = new_value

    @property
    def result(self) -> Any:
        return self._result

    @result.setter
    def result(self, new_value: Any) -> None:
        self._result = new_value

    def __enter__(self):

        try:
            self.run()
        except BaseException as ex:
            self.clean_up()
            raise ex

        return self.result

    def __exit__(self, exc_type, exc_val, exc_tb):
        # we could optionally call self.report() on exiting.
        self.clean_up()

    @classmethod
    def from_file(
        cls,
        project_root: str = "./",
        input_file: str = "./.taskcat.yml",
        regions: str = "ALL",
        enable_sig_v2: bool = False,
    ):
        """
        Creates a Test using a Taskcat config file.

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
        Creates a Test using a dictionary Taskcat config.

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
