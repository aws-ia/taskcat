import signal
import sys

import requests
from pkg_resources import get_distribution

from taskcat._cli_core import GLOBAL_ARGS, CliCore, _get_log_level
from taskcat._common_utils import exit_with_code
from taskcat._logger import PrintMsg, init_taskcat_cli_logger
from taskcat.exceptions import TaskCatException

from . import _cli_modules

LOG = init_taskcat_cli_logger(loglevel="ERROR")
BANNER = (
    " _            _             _   \n| |_ __ _ ___| | _____ __ _| |_ \n| __/ _"
    "` / __| |/ / __/ _` | __|\n| || (_| \\__ \\   < (_| (_| | |_ \n \\__\\__,_|"
    "___/_|\\_\\___\\__,_|\\__|\n                                \n"
)

NAME = "taskcat"
DESCRIPTION = (
    "taskcat is a tool that tests AWS CloudFormation templates. It deploys "
    "your AWS CloudFormation template in multiple AWS Regions and "
    "generates a report with a pass/fail grade for each region. You can "
    "specify the regions and number of Availability Zones you want to "
    "include in the test, and pass in parameter values from your AWS "
    "CloudFormation template."
)


def main(cli_core_class=CliCore, exit_func=exit_with_code):
    signal.signal(signal.SIGINT, _sigint_handler)
    log_level = _setup_logging(sys.argv)
    args = sys.argv[1:]
    if not args:
        args.append("-h")
    try:
        _welcome()
        version = get_installed_version()
        cli = cli_core_class(NAME, _cli_modules, DESCRIPTION, version, GLOBAL_ARGS.ARGS)
        cli.parse(args)
        _default_profile = cli.parsed_args.__dict__.get("_profile")
        if _default_profile:
            GLOBAL_ARGS.profile = _default_profile
        cli.run()
    except TaskCatException as e:
        LOG.error(str(e), exc_info=_print_tracebacks(log_level))
        exit_func(1)
    except Exception as e:  # pylint: disable=broad-except
        LOG.error(
            "%s %s", e.__class__.__name__, str(e), exc_info=_print_tracebacks(log_level)
        )
        exit_func(1)


def _setup_logging(args, exit_func=exit_with_code):
    log_level = _get_log_level(args, exit_func=exit_func)
    LOG.setLevel(log_level)
    return log_level


def _print_tracebacks(log_level):
    return log_level == "DEBUG"


def _print_upgrade_msg(new_version, version):
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


def check_for_update():
    version = get_installed_version()
    if version != "[local source] no pip module installed":
        if "dev" not in version:
            try:
                current_version = get_pip_version(f"https://pypi.org/pypi/{NAME}/json")
                if version in current_version:
                    LOG.info("version %s" % version, extra={"nametag": ""})
                else:
                    _print_upgrade_msg(current_version, version)
            except Exception:  # pylint: disable=broad-except
                LOG.debug("Unexpected error", exc_info=True)
                LOG.warning("Unable to get version info!!, continuing")
    else:
        LOG.info("Using local source (development mode)\n")


def _welcome():
    LOG.info(f"{BANNER}\n", extra={"nametag": ""})
    try:
        check_for_update()
    except Exception:  # pylint: disable=broad-except
        LOG.debug("Unexpected error", exc_info=True)
        LOG.warning("Unable to get version info!!, continuing")


def get_pip_version(url):
    """
    Given the url to PypI package info url returns the current live version
    """
    return requests.get(url, timeout=5.0).json()["info"]["version"]


def get_installed_version():
    try:
        return get_distribution(NAME).version
    except Exception:  # pylint: disable=broad-except
        return "[local source] no pip module installed"


def _sigint_handler(signum, frame):
    LOG.debug(f"SIGNAL {signum} caught at {frame}")
    exit_with_code(1)
