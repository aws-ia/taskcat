"""
TaskCat CLI Entry Point Module

This module provides the main command-line interface for TaskCat, an AWS CloudFormation
template testing tool. It handles CLI argument parsing, logging setup, version checking,
and error handling for the entire application.

The module serves as the primary entry point when TaskCat is invoked from the command line,
coordinating between various CLI modules and providing a consistent user experience.
"""

import importlib.metadata
import signal
import sys

import requests

from taskcat._cli_core import GLOBAL_ARGS, CliCore, _get_log_level
from taskcat._common_utils import exit_with_code
from taskcat._logger import PrintMsg, init_taskcat_cli_logger
from taskcat.exceptions import TaskCatException

from . import _cli_modules

# Initialize logger with ERROR level by default
LOG = init_taskcat_cli_logger(loglevel="ERROR")

# ASCII art banner displayed when TaskCat starts
BANNER = (
    " _            _             _   \n| |_ __ _ ___| | _____ __ _| |_ \n| __/ _"
    "` / __| |/ / __/ _` | __|\n| || (_| \\__ \\   < (_| (_| | |_ \n \\__\\__,_|"
    "___/_|\\_\\___\\__,_|\\__|\n                                \n"
)

# Application name used throughout the CLI
NAME = "taskcat"

# Application description shown in help text
DESCRIPTION = (
    "taskcat is a tool that tests AWS CloudFormation templates. It deploys "
    "your AWS CloudFormation template in multiple AWS Regions and "
    "generates a report with a pass/fail grade for each region. You can "
    "specify the regions and number of Availability Zones you want to "
    "include in the test, and pass in parameter values from your AWS "
    "CloudFormation template."
)


def main(cli_core_class=CliCore, exit_func=exit_with_code):
    """
    Main entry point for the TaskCat CLI application.
    
    This function orchestrates the entire CLI workflow including:
    - Signal handling setup for graceful interruption
    - Logging configuration
    - Command-line argument parsing
    - CLI module initialization and execution
    - Error handling and reporting
    
    Args:
        cli_core_class (class, optional): CLI core class to use for parsing and execution.
                                        Defaults to CliCore. Used for dependency injection
                                        in testing.
        exit_func (callable, optional): Function to call for program exit. 
                                      Defaults to exit_with_code. Used for testing.
    
    Raises:
        TaskCatException: For known TaskCat-specific errors
        Exception: For unexpected errors during execution
    """
    # Set up signal handler for graceful interruption (Ctrl+C)
    signal.signal(signal.SIGINT, _sigint_handler)
    
    # Configure logging based on command-line arguments
    log_level = _setup_logging(sys.argv)
    
    # Get command-line arguments, default to help if none provided
    args = sys.argv[1:]
    if not args:
        args.append("-h")
    
    try:
        # Display welcome banner and version information
        _welcome()
        
        # Get the currently installed version of TaskCat
        version = get_installed_version()
        
        # Initialize the CLI core with modules and configuration
        cli = cli_core_class(NAME, _cli_modules, DESCRIPTION, version, GLOBAL_ARGS.ARGS)
        
        # Parse the command-line arguments
        cli.parse(args)
        
        # Extract and set the AWS profile if specified
        _default_profile = cli.parsed_args.__dict__.get("_profile")
        if _default_profile:
            GLOBAL_ARGS.profile = _default_profile
        
        # Execute the parsed command
        cli.run()
        
    except TaskCatException as e:
        # Handle known TaskCat exceptions with appropriate logging
        LOG.error(str(e), exc_info=_print_tracebacks(log_level))
        exit_func(1)
    except Exception as e:  # pylint: disable=broad-except
        # Handle unexpected exceptions with full error details
        LOG.error(
            "%s %s", e.__class__.__name__, str(e), exc_info=_print_tracebacks(log_level)
        )
        exit_func(1)


def _setup_logging(args, exit_func=exit_with_code):
    """
    Configure logging level based on command-line arguments.
    
    Args:
        args (list): Command-line arguments to parse for log level
        exit_func (callable, optional): Function to call on exit. Defaults to exit_with_code.
    
    Returns:
        str: The configured log level (e.g., 'DEBUG', 'INFO', 'ERROR')
    """
    log_level = _get_log_level(args, exit_func=exit_func)
    LOG.setLevel(log_level)
    return log_level


def _print_tracebacks(log_level):
    """
    Determine whether to print full tracebacks based on log level.
    
    Args:
        log_level (str): Current logging level
    
    Returns:
        bool: True if tracebacks should be printed (DEBUG mode), False otherwise
    """
    return log_level == "DEBUG"


def _print_upgrade_msg(new_version, version):
    """
    Display upgrade notification message to the user.
    
    Shows available upgrade options for both pip and Docker installations
    when a newer version of TaskCat is available.
    
    Args:
        new_version (str): The latest available version
        version (str): The currently installed version
    """
    # Display current version
    LOG.info(f"version {version}\n", extra={"nametag": ""})
    
    # Warn about newer version availability
    LOG.warning("A newer version of %s is available (%s)", NAME, new_version)
    
    # Show pip upgrade command
    LOG.info(
        "To upgrade pip version    %s[ pip install --upgrade %s]%s",
        PrintMsg.highlight,
        NAME,
        PrintMsg.rst_color,
    )
    
    # Show Docker upgrade command
    LOG.info(
        "To upgrade docker version %s[ docker pull %s/%s ]%s\n",
        PrintMsg.highlight,
        NAME,
        NAME,
        PrintMsg.rst_color,
    )


def check_for_update():
    """
    Check for available TaskCat updates and notify the user.
    
    Compares the currently installed version with the latest version available
    on PyPI. Only checks for stable releases (non-dev versions) and handles
    various error conditions gracefully.
    
    The function will:
    - Skip update checks for development versions
    - Display current version information
    - Show upgrade instructions if a newer version is available
    - Handle network errors and API failures gracefully
    """
    version = get_installed_version()
    
    # Skip update check for local development installations
    if version != "[local source] no pip module installed":
        # Only check for updates on stable releases (not dev versions)
        if "dev" not in version:
            try:
                # Fetch latest version from PyPI
                current_version = get_pip_version(f"https://pypi.org/pypi/{NAME}/json")
                
                if version in current_version:
                    # Current version is up to date
                    LOG.info("version %s" % version, extra={"nametag": ""})
                else:
                    # Newer version available, show upgrade message
                    _print_upgrade_msg(current_version, version)
                    
            except Exception:  # pylint: disable=broad-except
                # Handle network errors, API failures, etc.
                LOG.debug("Unexpected error", exc_info=True)
                LOG.warning("Unable to get version info!!, continuing")
    else:
        # Running from local source (development mode)
        LOG.info("Using local source (development mode)\n")


def _welcome():
    """
    Display the TaskCat welcome banner and perform version checking.
    
    Shows the ASCII art banner and checks for available updates.
    Handles any errors during the welcome process gracefully to avoid
    interrupting the main application flow.
    """
    # Display the ASCII art banner
    LOG.info(f"{BANNER}\n", extra={"nametag": ""})
    
    try:
        # Check for available updates
        check_for_update()
    except Exception:  # pylint: disable=broad-except
        # Don't let version checking errors interrupt the application
        LOG.debug("Unexpected error", exc_info=True)
        LOG.warning("Unable to get version info!!, continuing")


def get_pip_version(url):
    """
    Retrieve the current version of a package from PyPI.
    
    Args:
        url (str): The PyPI JSON API URL for the package
        
    Returns:
        str: The latest version string from PyPI
        
    Raises:
        requests.RequestException: If the HTTP request fails
        KeyError: If the expected JSON structure is not found
        ValueError: If the JSON response is malformed
    """
    response = requests.get(url, timeout=5.0)
    return response.json()["info"]["version"]


def get_installed_version():
    """
    Get the currently installed version of TaskCat.
    
    Uses importlib.metadata to retrieve version information from the
    installed package metadata.
    
    Returns:
        str: The installed version string, or a special message for
             development installations
    """
    return importlib.metadata.version(__package__ or __name__)


def _sigint_handler(signum, frame):
    """
    Handle SIGINT (Ctrl+C) signal for graceful shutdown.
    
    Args:
        signum (int): The signal number that was received
        frame: The current stack frame when the signal was received
    """
    LOG.debug(f"SIGNAL {signum} caught at {frame}")
    exit_with_code(1)
