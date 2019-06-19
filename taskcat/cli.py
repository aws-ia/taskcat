import importlib
import signal
import sys
from pathlib import Path
from typing import List

import pyfiglet
import requests
from pkg_resources import get_distribution

import taskcat
from taskcat.cli_core import CliCore
from taskcat.common_utils import exit0, exit1
from taskcat.exceptions import TaskCatException
from taskcat.logger import init_taskcat_cli_logger, PrintMsg

LOG = init_taskcat_cli_logger(loglevel="ERROR")


NAME = "taskcat-v9"
GLOBAL_FLAGS = ["-q", "--quiet", "--debug"]  # these are processed before a config
# object is built and stripped from the args before they are passed to config


class Cli:
    MODULE_PATH = Path("cli_modules")

    def __init__(self, args: List[str]):
        self.args: List[str] = args if args is not None else []
        self._module_list: List[str] = self._get_plugin_module_names()
        self._module = None

    @classmethod
    def _get_plugin_module_names(cls):
        module_list = []
        full_path: Path = (Path(__file__).parent / cls.MODULE_PATH).resolve()
        if not full_path.exists():
            raise TaskCatException(
                f"{NAME} cli_modules folder {full_path} does not " f"exist"
            )
        files = [
            path
            for path in full_path.glob("*.py")
            if not path.stem.startswith("__") and path.is_file()
        ]
        if not files:
            raise TaskCatException(
                f"{NAME} cli_modules folder {full_path} does not "
                f"contain any modules"
            )
        _ = [module_list.append(file.stem) for file in files]
        return module_list

    @staticmethod
    def _print_version():
        print(get_installed_version())

    def _print_help(self):
        def _print_commands():
            for command in self._module_list:
                print(f"    {command}")

        print(
            f"usage: {NAME} [global_flags] <command> <subcommand> [options] \n"
            f"To see specific help text, you can run: \n"
            f"\n"
            f"{NAME} --help \n"
            f"{NAME} <command> --help \n"
            f"{NAME} <command> <subcommand> --help \n"
            f"\n"
            f"Global flags: \n"
            f"    --debug # enables debug output \n"
            f"    -q/--quiet # only output errors \n"
            f"\n"
            f"Available commands:"
        )
        _print_commands()

    def run(self):
        number_of_args = len(self.args)
        command = self.args[0] if not self.args else ""
        subcommand = self.args[1] if len(self.args) > 1 else ""
        options = self.args[2:] if len(self.args) > 2 else []

        # print global help
        if number_of_args == 0 or command == "--help":
            self._print_help()
            return
        # print version
        if command == "version":
            self._print_version()
            return
        # print help if command is invalid
        if command not in self._module_list:
            LOG.error(f"Invalid command {command}")
            self._print_help()
            return

        class_name = command.title()
        module_name = f"taskcat.{Cli.MODULE_PATH}.{command}"
        plugin = self._import_plugin_module(class_name, module_name)
        cli_core = CliCore(plugin)
        available_subcommands = [subcomm[0] for subcomm in cli_core.get_methods()]
        # print command help
        LOG.debug(available_subcommands)
        print(options)
        if subcommand not in available_subcommands:
            if subcommand not in ["--help", "-h"]:
                LOG.error(f"Invalid subcommnand {subcommand}")
            self._print_command_help(command, available_subcommands)
            return

        cli_core.call_method(subcommand, options)

    @staticmethod
    def _print_command_help(cmd, methods):
        msg = (
            f"\nusage: {NAME} {cmd} <subcommand> [options] \n"
            "To see help text, you can run: \n"
            "\n"
            f"{NAME} {cmd} --help \n"
            f"{NAME} {cmd} <subcommand> --help \n"
            "\n"
            "SUB-COMMANDS: \n"
        )
        for name in methods:
            if not name.startswith("__"):
                msg = msg + "    " + name + "\n"
        print(msg)

    @staticmethod
    def _import_plugin_module(class_name, module_name):
        return getattr(importlib.import_module(module_name), class_name)


def main():
    args = sys.argv[1:]
    log_level = _setup_logging(args)
    signal.signal(signal.SIGINT, _sigint_handler)
    try:
        _welcome()
        _remove_global_flags(args)
        cli = Cli(args)
        cli.run()
    except taskcat.exceptions.TaskCatException as e:
        LOG.error(str(e), exc_info=_print_tracebacks(log_level))
        exit1()
    except Exception as e:  # pylint: disable=broad-except
        LOG.error(
            "%s %s", e.__class__.__name__, str(e), exc_info=_print_tracebacks(log_level)
        )
        exit1()
    exit0()


def _setup_logging(args):
    log_level = _get_log_level(args)
    LOG.setLevel(log_level)
    return log_level


def _print_tracebacks(log_level):
    return log_level == "DEBUG"


def _get_log_level(args):
    log_level = "INFO"
    if "--debug" in args and ("-q" in args or "--quiet" in args):
        exit1("--debug and --quiet cannot be specified simultaneously")
    if "--debug" in args:
        log_level = "DEBUG"
    if "-q" in args or "--quiet" in args:
        log_level = "ERROR"
    return log_level


def _remove_global_flags(args):
    for item in GLOBAL_FLAGS:
        try:
            args.remove(item)
        except ValueError:
            pass


def check_for_update():
    def _print_upgrade_msg(new_version):
        LOG.info("version %s\n" % version, extra={"nametag": ""})
        LOG.warning("A newer version of %s is available (%s)", NAME, new_version)
        LOG.info(
            "To upgrade pip version    %s[ pip install --upgrade %s]%s",
            PrintMsg.highlight,
            NAME,
            PrintMsg.rst_color,
        )
        LOG.info(
            "To upgrade docker version %s[ docker pull %s/%s ]%s\n",
            PrintMsg.highlight,
            NAME,
            NAME,
            PrintMsg.rst_color,
        )

    version = get_installed_version()
    if version != "[local source] no pip module installed":
        if "dev" not in version:
            current_version = get_pip_version(f"https://pypi.org/pypi/{NAME}/json")
            if version in current_version:
                LOG.info("version %s" % version, extra={"nametag": ""})
            else:
                _print_upgrade_msg(current_version)
    else:
        LOG.info("Using local source (development mode)\n")


def _welcome():
    banner = pyfiglet.Figlet(font="standard")
    banner = banner
    LOG.info(f"{banner.renderText(NAME)}\n", extra={"nametag": ""})
    try:
        check_for_update()
    except TaskCatException:
        raise
    except Exception:  # pylint: disable=broad-except
        LOG.debug("Unexpected error", exc_info=True)
        LOG.warning("Unable to get version info!!, continuing")


def get_pip_version(url):
    """
    Given the url to PypI package info url returns the current live version
    """
    return requests.get(url).json()["info"]["version"]


def get_installed_version():
    try:
        return get_distribution(NAME).version.replace(".0", ".")
    except Exception:  # pylint: disable=broad-except
        return "[local source] no pip module installed"


def _sigint_handler(signum, frame):
    LOG.debug(f"SIGNAL {signum} caught at {frame}")
    exit1()
