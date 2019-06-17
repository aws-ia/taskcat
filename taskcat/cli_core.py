# This should ultimately become it's own module, as it has great general purpose
# utility.

import argparse
import inspect
import logging
from typing import List
from pathlib import Path
from taskcat.exceptions import TaskCatException

logger = logging.getLogger(__name__)


class InvalidActionError(TaskCatException):
    """Exception raised for error when invalid action is supplied

    Attributes:
        expression -- input expression in which the error occurred
    """

    def __init__(self, expression):
        self.expression = expression


class CliCore:

    def __init__(self, module_path: Path, description, usage, version=None):
        self.module_path = module_path
        self._module_list: List[str] = self._get_plugin_module_names()
        self.parser = self._build_base_parser(description, usage, version)

    def _build_base_parser(self, description, usage, version):
        parser = argparse.ArgumentParser(description=description, usage=usage)
        if version:
            parser.add_argument('-v', '--version', action='version', version=version)
        return parser

    def _get_plugin_module_names(self):
        module_list = []
        full_path: Path = (Path(__file__).parent / self.module_path).resolve()
        if not full_path.exists():
            raise TaskCatException(
                f"{NAME} cli_modules folder {full_path} does not "
                f"exist")
        files = [
            path for path in full_path.glob('*.py')
            if not path.stem.startswith('__')
               and path.is_file()
        ]
        if not files:
            raise TaskCatException(
                f"{NAME} cli_modules folder {full_path} does not "
                f"contain any modules")
        [module_list.append(file.stem) for file in files]
        return module_list

    def _print_help(self):

        def _print_commands():
            for command in self._module_list:
                print(f"    {command}")

        print(f"usage: {NAME} [global_flags] <command> <subcommand> [options] \n"
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
              f"Available commands:")
        _print_commands()

    def run(self):
        number_of_args = len(self.args)
        command = self.args[0] if len(self.args) > 0 else ''
        subcommand = self.args[1] if len(self.args) > 1 else ''
        options = self.args[2:] if len(self.args) > 2 else []

        # print global help
        if number_of_args == 0 or command == "--help":
            self._print_help()
            return
        # print version
        if command == 'version':
            self._print_version()
            return
        # print help if command is invalid
        if command not in self._module_list:
            log.error(f"Invalid command {command}")
            self._print_help()
            return

        class_name = command.title()
        module_name = f"taskcat.{Cli.MODULE_PATH}.{command}"
        plugin = self._import_plugin_module(class_name, module_name)
        cli_core = CliCore(plugin)
        available_subcommands = [subcomm[0] for subcomm in cli_core.get_methods()]
        # print command help
        log.debug(available_subcommands)
        print(options)
        if subcommand not in available_subcommands:
            if subcommand not in ['--help', '-h']:
                log.error(f"Invalid subcommnand {subcommand}")
            self._print_command_help(command, available_subcommands)
            return

        cli_core.call_method(subcommand, options)

    @staticmethod
    def _print_command_help(cmd, methods):
        msg = f"\nusage: {NAME} {cmd} <subcommand> [options] \n" \
            "To see help text, you can run: \n" \
            "\n" \
            f"{NAME} {cmd} --help \n" \
            f"{NAME} {cmd} <subcommand> --help \n" \
            "\n" \
            "SUB-COMMANDS: \n"
        for name in methods:
            if not name.startswith('__'):
                msg = msg + "    " + name + "\n"
        print(msg)

    @staticmethod
    def _import_plugin_module(class_name, module_name):
        return getattr(importlib.import_module(module_name), class_name)

class CliModule:

    def __init__(self, module):
        self.module_name = module.__name__
        self.module = module

    def call_method(self, action, arguments):
        """Call method named action from self.module, with arguments containing cli
        options/flags"""
        for name, method in inspect.getmembers(self.module(),
                                               predicate=inspect.ismethod):
            if name == action:
                # If method with name 'action' found in the module,
                # create argparser for that method, parse cli arguments,
                # and invoke method
                logger.debug("Creating parser for function {}".format(name))
                parser = self.create_argparse(method)
                kwargs = vars(parser.parse_args(arguments))
                logger.debug(kwargs)
                method(**kwargs)
                return
        # Invalid action provided, raise InvalidActionError
        raise InvalidActionError("Invalid sub-subcommand {} for module {}".format(
            action, self.module_name.lower()))

    def get_methods(self):
        """Return list of available methods"""
        logger.debug('Returns list of methods for module ' + self.module_name)
        return inspect.getmembers(self.module, predicate=inspect.ismethod)

    def create_argparse(self, method):
        logger.debug("Method doc string -> " + str(method.__doc__))
        logger.debug("whose signature is -> {}".format(inspect.signature(method)))
        # Create arg parser for module.method with parameters as options
        # By default, all method parameters are required
        arg_parser = argparse.ArgumentParser(
            description=str(method.__doc__),
            usage=f'%(prog)s {self.module_name.lower()} {method.__name__} [options]'
        )
        optional_group = arg_parser._action_groups.pop()
        required_group = arg_parser.add_argument_group('required arguments')

        arg_type = type("str")
        required_switch = True

        sig = inspect.signature(method)
        for param in sig.parameters.values():
            logger.debug("{} is of type {} with default value {}"
                         .format(param.name, param.annotation, param.default))
            # Check if parameter type is explicitly defined
            if param.annotation != param.empty:
                arg_type = param.annotation

            # check if parameter has default value.
            # if yes, add it as optional flag
            if param.default != param.empty:
                required_switch = False
                group = optional_group
            else:
                group = required_group

            logger.debug("type -> {}".format(arg_type))
            group.add_argument(
                str("--" + str(param.name)),
                type=arg_type,
                required=required_switch,
                default=argparse.SUPPRESS)

        arg_parser._action_groups.append(optional_group)
        return arg_parser

    def get_module(self):
        """Getter - module"""
        return self.module()
