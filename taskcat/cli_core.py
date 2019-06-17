# This should ultimately become it's own module, as it has great general purpose
# utility.

import argparse
import inspect
import logging
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

    def __init__(self, module):
        self.module_name = module.__name__
        self.module = module()
        logger.debug("{0} is instance of {1}".format(self.module_name,
                                                     type(self.module)))

    def call_method(self, action, arguments):
        """Call method named action from self.module, with arguments containing cli
        options/flags"""
        for name, method in inspect.getmembers(self.module, predicate=inspect.ismethod):
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
        # arg_parser.parse_args(['-h'])
        return arg_parser

    def get_module(self):
        """Getter - module"""
        return self.module
