#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function

import json
import logging
import os
import sys
import yaml
import re
from collections import OrderedDict
from taskcat.exceptions import TaskCatException

class Logger(object):
    """Wrapper for a logging object that logs in json"""

    def __init__(self, request_id=None, log_format='json', loglevel='warning', botolevel='critical'):
        """Initializes logging with request_id"""
        self.request_id = request_id
        self.log_format = log_format
        self.config(request_id, loglevel=loglevel, botolevel=botolevel)
        return

    def config(self, request_id=None, original_job_id=None, job_id=None,
               artifact_revision_id=None, pipeline_execution_id=None, pipeline_action=None,
               stage_name=None, pipeline_name=None, loglevel='warning', botolevel='critical'):
        """Configures logging object

        Args:
            request_id (str): request id.
            original_job_id (str): [optional] pipeline job_id from first request in this run.
            job_id (str): [optional] pipeline job_id for the current invocation (differs from original_job_id if this is a continuation invocation).
            artifact_revision_id (str): [optional] commit id for current revision.
            pipeline_execution_id (str): [optional] pipeline execution id (same for all actions/stages in this pipeline run).
            pipeline_action (str): [optional] pipeline action name.
            stage_name (str): [optional] pipeline stage name.
            pipeline_name (str): [optional] pipeline name.
            loglevel (str): [optional] logging verbosity, defaults to warning.
            botolevel (str): [optional] boto logging verbosity, defaults to critical.
        """

        loglevel = getattr(logging, loglevel.upper(), 20)
        botolevel = getattr(logging, botolevel.upper(), 40)
        mainlogger = logging.getLogger()
        mainlogger.setLevel(loglevel)
        logging.getLogger('boto3').setLevel(botolevel)
        logging.getLogger('botocore').setLevel(botolevel)
        logging.getLogger('nose').setLevel(botolevel)
        logging.getLogger('s3transfer').setLevel(botolevel)
        if self.log_format == 'json':
            logfmt = '{"time_stamp": "%(asctime)s", "log_level": "%(levelname)s", "data": %(message)s}\n'
        elif self.log_format == 'logfile':
            logfmt = '%(asctime)s %(levelname)s %(message)s\n'
        else:
            logfmt = '%(message)s\n'
        if len(mainlogger.handlers) == 0:
            mainlogger.addHandler(logging.StreamHandler())
        mainlogger.handlers[0].setFormatter(logging.Formatter(logfmt))
        self.log = logging.LoggerAdapter(mainlogger, {})
        self.request_id = request_id
        self.original_job_id = original_job_id
        self.job_id = job_id
        self.pipeline_execution_id = pipeline_execution_id
        self.artifact_revision_id = artifact_revision_id
        self.pipeline_action = pipeline_action
        self.stage_name = stage_name
        self.pipeline_name = pipeline_name

    def set_boto_level(self, botolevel):
        """sets boto logging level

        Args:
        botolevel (str): boto3 logging verbosity (critical|error|warning|info|debug)
        """

        botolevel = getattr(logging, botolevel.upper(), 40)
        logging.getLogger('boto3').setLevel(botolevel)
        logging.getLogger('botocore').setLevel(botolevel)
        logging.getLogger('nose').setLevel(botolevel)
        logging.getLogger('s3transfer').setLevel(botolevel)
        return

    def _format(self, message):
        if self.log_format == 'json':
            message = self._format_json(message)
        else:
            message = str(message)
        print(message)
        return message

    def _format_json(self, message):
        """formats log message in json

        Args:
        message (str): log message, can be a dict, list, string, or json blob
        """

        metadata = {}
        if self.request_id:
            metadata["request_id"] = self.request_id
        if self.original_job_id:
            metadata["original_job_id"] = self.original_job_id
        if self.pipeline_execution_id:
            metadata["pipeline_execution_id"] = self.pipeline_execution_id
        if self.pipeline_name:
            metadata["pipeline_name"] = self.pipeline_name
        if self.stage_name:
            metadata["stage_name"] = self.stage_name
        if self.artifact_revision_id:
            metadata["artifact_revision_id"] = self.artifact_revision_id
        if self.pipeline_action:
            metadata["pipeline_action"] = self.pipeline_action
        if self.job_id:
            metadata["job_id"] = self.job_id
        try:
            message = json.loads(message)
        except TaskCatException:
            raise
        except Exception:
            pass
        try:
            metadata["message"] = message
            return json.dumps(metadata)
        except TaskCatException:
            raise
        except Exception:
            metadata["message"] = str(message)
            return json.dumps(metadata)

    def debug(self, message, **kwargs):
        """wrapper for logging.debug call"""
        self.log.debug(self._format(message), **kwargs)

    def info(self, message, **kwargs):
        """wrapper for logging.info call"""
        self.log.info(self._format(message), **kwargs)

    def warning(self, message, **kwargs):
        """wrapper for logging.warning call"""
        self.log.warning(self._format(message), **kwargs)

    def error(self, message, **kwargs):
        """wrapper for logging.error call"""
        self.log.error(self._format(message), **kwargs)

    def critical(self, message, **kwargs):
        """wrapper for logging.critical call"""
        self.log.critical(self._format(message), **kwargs)


class CFNYAMLHandler(object):
    """Handles the loading and dumping of CloudFormation YAML templates.

    Example usage:

    from taskcat import utils

    class MyClass(object):
        def __init__(self):
            # init MyClass
            return
        def my_load_yaml_function(self, template_file):
            template_data = utils.CFNYAMLHandler.ordered_safe_load(open(template_file, 'rU'), object_pairs_hook=OrderedDict))
            return template_data
        def my_dump_yaml_function(self, template_data, output_file):
            utils.CFNYAMLHandler.validate_output_dir(output_file)
            with open(output_file, 'wb') as updated_template:
                updated_template.write(utils.CFNYAMLHandler.ordered_safe_dump(template_data, indent=2, allow_unicode=True, default_flow_style=False, explicit_start=True, explicit_end=True))
            updated_template.close()
    """

    def __init__(self, logger=None, loglevel='error', botolevel='error'):
        """Sets up the logging object

        Args:
            logger (obj): a logging instance
        """

        if not logger:
            loglevel = getattr(logging, loglevel.upper(), 20)
            botolevel = getattr(logging, botolevel.upper(), 40)
            mainlogger = logging.getLogger()
            mainlogger.setLevel(loglevel)
            logging.getLogger('boto3').setLevel(botolevel)
            logging.getLogger('botocore').setLevel(botolevel)
            logging.getLogger('nose').setLevel(botolevel)
            logging.getLogger('s3transfer').setLevel(botolevel)
            if len(mainlogger.handlers) == 0:
                mainlogger.addHandler(logging.StreamHandler())
        else:
            self.logger = logger
        return

    @staticmethod
    def ordered_safe_load(stream, object_pairs_hook=OrderedDict):
        class OrderedSafeLoader(yaml.SafeLoader):
            pass

        def _construct_int_without_octals(loader, node):
            value = str(loader.construct_scalar(node)).replace('_', '')
            try:
                return int(value, 10)
            except ValueError:
                return loader.construct_yaml_int(node)

        def _construct_mapping(loader, node):
            loader.construct_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))

        def _construct_cfn_tag(loader, tag_suffix, node):
            tag_suffix = u'!{}'.format(tag_suffix)
            if isinstance(node, yaml.ScalarNode):
                # Check if block literal. Inject for later use in the YAML dumps.
                if node.style == '|':
                    return u'{0} {1} {2}'.format(tag_suffix, '|', node.value)
                else:
                    return u'{0} {1}'.format(tag_suffix, node.value)
            elif isinstance(node, yaml.SequenceNode):
                constructor = loader.construct_sequence
            elif isinstance(node, yaml.MappingNode):
                constructor = loader.construct_mapping
            else:
                raise BaseException('[ERROR] Unknown tag_suffix: {}'.format(tag_suffix))

            return OrderedDict([(tag_suffix, constructor(node))])

        OrderedSafeLoader.add_constructor(u'tag:yaml.org,2002:int', _construct_int_without_octals)
        OrderedSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)
        OrderedSafeLoader.add_multi_constructor('!', _construct_cfn_tag)

        return yaml.safe_load(stream, OrderedSafeLoader)

    @staticmethod
    def ordered_safe_dump(data, stream=None, **kwds):
        class OrderedSafeDumper(yaml.SafeDumper):
            pass

        def _dict_representer(dumper, _data):
            return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _data.items())

        def _str_representer(dumper, _data):
            if re.match('!\w+\s+\|.+', _data):
                tag = re.search('^!\w+', _data).group(0)
                return dumper.represent_scalar(str(tag), _data.split('|', 1)[1].lstrip(), style='|')
            elif len(_data.splitlines()) > 1:
                return dumper.represent_scalar('tag:yaml.org,2002:str', _data, style='|')
            else:
                return dumper.represent_str(_data)

        OrderedSafeDumper.add_representer(OrderedDict, _dict_representer)
        OrderedSafeDumper.add_implicit_resolver('tag:yaml.org,2002:int', re.compile('^[-+]?[0-9][0-9_]*$'), list('-+0123456789'))
        OrderedSafeDumper.add_representer(str, _str_representer)
        OrderedSafeDumper.ignore_aliases = lambda self, data: True

        yaml_dump = yaml.safe_dump(data, stream, OrderedSafeDumper, **kwds)

        # CloudFormation !Tag quote/colon cleanup
        keyword = re.search('\'!.*\':?', yaml_dump)
        while keyword:
            yaml_dump = re.sub(re.escape(keyword.group(0)), keyword.group(0).strip('\'":'), yaml_dump)
            keyword = re.search('\'!.*\':?', yaml_dump)

        return yaml_dump

    @staticmethod
    def validate_output_dir(directory):
        if os.path.isfile(directory):
            directory = os.path.split(directory)[0]
        if not os.path.isdir(directory):
            # TODO: FIX LOG LINE
            print("[INFO]: Directory [{}] does not exist. Trying to create it.".format(directory))
            # logger.info("[INFO]: Directory [{}] does not exist. Trying to create it.".format(directory))
            os.makedirs(directory)
        elif not os.access(directory, os.W_OK):
            pass
            # TODO: FIX LOG LINE AND EXITING. REMOVE PASS ABOVE.
            print("[ERROR]: No write access allowed to output directory [{}]. Aborting.".format(directory))
            # logger.error("[ERROR]: No write access allowed to output directory [{}]. Aborting.".format(directory))
            sys.exit(1)
