# This should ultimately become it's own module, as it has great general purpose
# utility.

import argparse
import importlib
import inspect
import logging
import sys
import types

LOG = logging.getLogger(__name__)


class CliCore:
    USAGE = "{prog}{global_opts}{command}{command_opts}{subcommand}{subcommand_opts}"

    def __init__(self, prog_name, module_package, description, version=None, args=None):
        self.name = prog_name
        self.module_package = module_package
        self._modules = self._get_plugin_modules()
        self.args = {"global": args if args is not None else [], "commands": {}}
        self._build_args()
        self.command_parser = None
        self.subcommand_parsers = {}
        self.parser = self._build_parser(description, version)
        self.parsed_args = []

    def _build_args(self):
        for name, module in self._modules.items():
            params = self._get_params(module)
            self.args["commands"][name] = {"args": params, "subcommands": {}}
            for method_name, method_function in self._get_class_methods(module):
                if not method_name.startswith("_"):
                    params = self._get_params(method_function)
                    self.args["commands"][name]["subcommands"][method_name] = params

    @staticmethod
    def _get_class_methods(module):
        methods = inspect.getmembers(module, predicate=inspect.isfunction)
        return [method for method in methods if not method[0].startswith("_")]

    @staticmethod
    def _get_params(item):
        params = []
        for param in inspect.signature(item).parameters.values():
            if param.name == "self" or param.name.startswith("_"):
                continue
            required = param.default == param.empty
            default = param.default if not required else None
            val_type = param.annotation if param.annotation in [str, int, bool] else str
            action = "store_true" if val_type == bool else "store"
            param_help = CliCore._get_param_help(item, param.name)
            name = param.name.lower()
            kwargs = {"action": action, "help": param_help}
            if not required:
                name = name.replace("_", "-")
                kwargs.update(
                    {"required": required, "default": default, "dest": param.name}
                )
            if action == "store":
                kwargs.update({"type": val_type})
            if required:
                params.append([[name], kwargs])
            else:
                if name in getattr(item, 'longform_required', []):
                    params.append([[f"--{name}"], kwargs])
                else:
                    params.append([[f"-{name[0]}", f"--{name}"], kwargs])
        return params

    @staticmethod
    def _get_param_help(item, param):
        help_str = ""
        docstring = (
            item.__doc__
            if isinstance(item, types.FunctionType)
            else item.__init__.__doc__
        )
        if docstring is None:
            return help_str
        for line in docstring.split("\n"):
            if line.strip().startswith(f":param {param}:"):
                help_str = line.strip()[len(f":param {param}:") :].strip()
                break
        return help_str

    @staticmethod
    def _get_help(item):
        help_str = ""
        if item.__doc__ is None:
            return help_str
        for line in item.__doc__.split("\n"):
            if not line.strip().startswith(":"):
                help_str += line.strip()
        return help_str.strip()

    def _get_command_help(self, commands):
        help_str = ""
        for name, mod in commands.items():
            mod_help = self._get_help(mod)
            if not mod_help:
                help_str += f"{name}\n"
            else:
                help_str += f"{name} - {mod_help}\n"
        return help_str.strip()

    def _add_subparser(self, usage, description, mod, parser, args):
        sub_parser = parser.add_parser(
            mod,
            usage=usage,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        self._add_arguments(args, sub_parser)
        return sub_parser

    @staticmethod
    def _add_arguments(input_args, parser):
        for args, kwargs in input_args:
            parser.add_argument(*args, **kwargs)

    @staticmethod
    def _add_sub(parser, **kwargs):
        if sys.version_info[1] != 6 or "required" not in kwargs:
            return parser.add_subparsers(**kwargs)
        required = kwargs["required"]
        kwargs.pop("required")
        sub = parser.add_subparsers(**kwargs)
        sub.required = required
        return sub

    def _build_parser(self, description, version):
        parser = argparse.ArgumentParser(
            description=description,
            usage=self._build_usage(),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        if version:
            parser.add_argument("-v", "--version", action="version", version=version)
        # Add global arguments
        self._add_arguments(self.args["global"], parser)

        description = self._get_command_help(self._modules)
        command_parser = self._add_sub(
            parser=parser,
            title="commands",
            description=description,
            required=True,
            metavar="",
            dest="_command",
        )
        self.command_parser = command_parser
        for mod in self._modules:
            usage = self._build_usage({"command": mod})
            description = self._get_help(self._modules[mod])
            mod_parser = self._add_subparser(
                usage,
                description,
                mod,
                command_parser,
                self.args["commands"][mod]["args"],
            )
            self.subcommand_parsers[mod] = mod_parser
            # add subcommand parser if subcommands exist
            subcommands = self.args["commands"][mod]["subcommands"]
            if subcommands:
                class_methods = {
                    m[0]: m[1] for m in self._get_class_methods(self._modules[mod])
                }
                description = self._get_command_help(class_methods)
                subcommand_parser = self._add_sub(
                    parser=mod_parser,
                    title="subcommands",
                    description=description,
                    required=True,
                    metavar="",
                    dest="_subcommand",
                )
                for subcommand_name, subcommand_args in subcommands.items():
                    usage = self._build_usage({"subcommand": subcommand_name})
                    description = self._get_help(class_methods[subcommand_name])
                    self._add_subparser(
                        usage,
                        description,
                        subcommand_name,
                        subcommand_parser,
                        subcommand_args,
                    )
        return parser

    def _build_usage(self, args=None):
        args = args if args is not None else {}
        args["prog"] = self.name
        if "command" not in args:
            args["command"] = "<command>"
        if "subcommand" not in args:
            args["subcommand"] = "[subcommand]"
        if "global_opts" not in args:
            args["global_opts"] = "[args]"
        if "command_opts" not in args:
            args["command_opts"] = "[args]"
        if "subcommand_opts" not in args:
            args["subcommand_opts"] = "[args]"
        for key, val in args.items():
            if val and not val.endswith(" "):
                args[key] = f"{val} "
        return self.USAGE.format(**args)

    def _get_plugin_modules(self):
        # pylint: disable=invalid-name
        members = inspect.getmembers(self.module_package, predicate=inspect.isclass)
        member_name_class = []
        for name, cls in members:
            if hasattr(cls, "CLINAME"):
                name = cls.CLINAME
            member_name_class.append((name, cls))
        x = {name.lower(): cls for name, cls in member_name_class}
        return x

    @staticmethod
    def _import_plugin_module(class_name, module_name):
        return getattr(importlib.import_module(module_name), class_name)

    def parse(self, args=None):
        if not args:
            args = []
        self.parsed_args = self.parser.parse_args(args)
        return self.parsed_args

    def run(self):
        args = self.parsed_args.__dict__
        command = self._modules[args["_command"]]
        subcommand = ""
        if "_subcommand" in args:
            subcommand = args["_subcommand"]
        args = {k: v for k, v in args.items() if not k.startswith("_")}
        if not subcommand:
            return command(**args)
        return getattr(command(), subcommand)(**args)

def ignore_param_generation(param_name):
    def wrapper(func):
        if hasattr(func, 'no_param_generate'):
            func.longform_required.append(param_name.replace('_', '-'))
        else:
            setattr(func, 'no_param_generate', [param_name.replace('_', '-')])

def longform_param_required(param_name):
    def wrapper(func):
        if hasattr(func, 'longform_required'):
            func.longform_required.append(param_name.replace('_', '-'))
        else:
            setattr(func, 'longform_required', [param_name.replace('_', '-')])
        return func
    return wrapper
