#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function

import logging
import os
import re
from collections import OrderedDict

import yaml

from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class CFNYAMLHandler:
    """Handles the loading and dumping of CloudFormation YAML templates.

    Example usage:

    from taskcat import utils

    class MyClass(object):
        def __init__(self):
            # init MyClass
            return
        def my_load_yaml_function(self, template_file):
            template_data = utils.CFNYAMLHandler.ordered_safe_load(open(template_file,
                'rU'), object_pairs_hook=OrderedDict))
            return template_data
        def my_dump_yaml_function(self, template_data, output_file):
            utils.CFNYAMLHandler.validate_output_dir(output_file)
            with open(output_file, 'wb') as updated_template:
                updated_template.write(utils.CFNYAMLHandler.ordered_safe_dump(
                    template_data, indent=2, allow_unicode=True,
                    default_flow_style=False, explicit_start=True, explicit_end=True))
            updated_template.close()
    """

    def __init__(self):
        return

    @staticmethod
    def ordered_safe_load(stream, object_pairs_hook=OrderedDict):
        class OrderedSafeLoader(yaml.SafeLoader):  # pylint: disable=too-many-ancestors
            pass

        def _construct_int_without_octals(loader, node):
            value = str(loader.construct_scalar(node)).replace("_", "")
            try:
                return int(value, 10)
            except ValueError:
                return loader.construct_yaml_int(node)

        def _construct_mapping(loader, node):
            loader.construct_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))

        def _construct_cfn_tag(loader, tag_suffix, node):
            tag_suffix = "!{}".format(tag_suffix)
            if isinstance(node, yaml.ScalarNode):
                # Check if block literal. Inject for later use in the YAML dumps.
                if node.style == "|":
                    return "{0} {1} {2}".format(tag_suffix, "|", node.value)
                return "{0} {1}".format(tag_suffix, node.value)
            if isinstance(node, yaml.SequenceNode):
                constructor = loader.construct_sequence
            elif isinstance(node, yaml.MappingNode):
                constructor = loader.construct_mapping
            else:
                raise BaseException("[ERROR] Unknown tag_suffix: {}".format(tag_suffix))

            return OrderedDict([(tag_suffix, constructor(node))])

        OrderedSafeLoader.add_constructor(
            "tag:yaml.org,2002:int", _construct_int_without_octals
        )
        OrderedSafeLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
        )
        OrderedSafeLoader.add_multi_constructor("!", _construct_cfn_tag)

        return yaml.load(stream, OrderedSafeLoader)  # nosec

    @staticmethod
    def ordered_safe_dump(data, _=None, **kwds):
        class OrderedSafeDumper(yaml.SafeDumper):  # pylint: disable=too-many-ancestors
            pass

        def _dict_representer(dumper, _data):
            return dumper.represent_mapping(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _data.items()
            )

        def _str_representer(dumper, _data):
            if re.match(r"!\w+\s+\|.+", _data):
                tag = re.search(r"^!\w+", _data).group(0)
                return dumper.represent_scalar(
                    str(tag), _data.split("|", 1)[1].lstrip(), style="|"
                )
            if len(_data.splitlines()) > 1:
                return dumper.represent_scalar(
                    "tag:yaml.org,2002:str", _data, style="|"
                )
            return dumper.represent_str(_data)

        OrderedSafeDumper.add_representer(OrderedDict, _dict_representer)
        OrderedSafeDumper.add_implicit_resolver(
            "tag:yaml.org,2002:int",
            re.compile("^[-+]?[0-9][0-9_]*$"),
            list("-+0123456789"),
        )
        OrderedSafeDumper.add_representer(str, _str_representer)
        OrderedSafeDumper.ignore_aliases = lambda self, data: True

        yaml_dump = yaml.dump(data, Dumper=OrderedSafeDumper, **kwds)

        # CloudFormation !Tag quote/colon cleanup
        keyword = re.search("'!.*':?", yaml_dump)
        while keyword:
            yaml_dump = re.sub(
                re.escape(keyword.group(0)), keyword.group(0).strip("'\":"), yaml_dump
            )
            keyword = re.search("'!.*':?", yaml_dump)

        return yaml_dump

    @staticmethod
    def validate_output_dir(directory):
        if os.path.isfile(directory):
            directory = os.path.split(directory)[0]
        if not os.path.isdir(directory):
            LOG.info(
                "Directory [{}] does not exist. Trying to create it.".format(directory)
            )
            os.makedirs(directory)
        elif not os.access(directory, os.W_OK):
            raise TaskCatException(
                f"No write access allowed to output directory "
                f"[{directory}]. Aborting."
            )
