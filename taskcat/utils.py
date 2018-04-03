#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Santiago Cardenas <sancard@amazon.com>
# Jay McConnell <jmmccon@amazon.com>
from __future__ import print_function

import boto3
import botocore
import json
import logging
import os
from threading import Lock
from time import sleep
import sys
import yaml
import re
from collections import OrderedDict


class ClientFactory(object):
    """Manages creating and caching boto3 clients, helpful when creating lots of
    clients in different regions or functions.

    Example usage:

    from tackcat import utils

    class MyClass(object):
        def __init__(self):
            self._boto_client = utils.ClientFactory()
        def my_function(self):
            s3_client = self._boto_client.get('s3', region='us-west-2')
            return s3_client.list_buckets()
    """

    def __init__(self, logger=None, loglevel='error', botolevel='error', aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None, profile_name=None):
        """Sets up the cache dict, a locking mechanism and the logging object

        Args:
            logger (obj): a logging instance
            loglevel (str): [optional] log verbosity, defaults to 'error'
            botolevel (str): [optional] boto3 log verbosity, defaults to 'error'
            aws_access_key_id (str): [optional] IAM access key, defaults to None
            aws_secret_access_key (str): [optional] IAM secret key, defaults to None
            aws_session_token (str): [optional] IAM session token, defaults to None
            profile_name (str): [optional] credential profile to use, defaults to None
        """
        self._clients = {"default": {}}
        self._credential_sets = {}
        self._lock = Lock()
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
            self.logger = mainlogger
        else:
            self.logger = logger
        self.put_credential_set('default', aws_access_key_id, aws_secret_access_key, aws_session_token, profile_name)
        return

    def put_credential_set(self, credential_set_name, aws_access_key_id=None, aws_secret_access_key=None,
                           aws_session_token=None, profile_name=None):
        """Adds or updates a credential set to be re-used when creating clients

                    aws_access_key_id (str): [optional] IAM access key, defaults to None
                    aws_secret_access_key (str): [optional] IAM secret key, defaults to None
                    aws_session_token (str): [optional] IAM session token, defaults to None
                    profile_name (str): [optional] credential profile to use, defaults to None
        """
        if (aws_access_key_id and not aws_secret_access_key) or (not aws_access_key_id and aws_secret_access_key):
            raise ValueError('"aws_access_key_id" and "aws_secret_access_key" must both be set')
        elif profile_name and (aws_access_key_id or aws_secret_access_key or aws_session_token):
            raise ValueError(
                '"profile_name" cannot be used with aws_access_key_id, aws_secret_access_key or aws_session_token')
        self._credential_sets[credential_set_name] = [aws_access_key_id, aws_secret_access_key, aws_session_token,
                                                      profile_name]

    def get(self, service, region=None, credential_set='default', aws_access_key_id=None,
            aws_secret_access_key=None, aws_session_token=None, s3v4=False, profile_name=None):
        """get a client for a given service and region, optionally with specific role, credentials and/or sig version

        Args:
            service (str): service name
            region (str): [optional] region name, defaults to current region
            credential_set (str): [optional] name used to seperate different sets of
                        credentials, defaults to "default" which uses either the auto-discovered
                        role, or the credentials configured when this class is instantiated
            aws_access_key_id (str): [optional] IAM access key, defaults to None
            aws_secret_access_key (str): [optional] IAM secret key, defaults to None
            aws_session_token (str): [optional] IAM session token, defaults to None
            s3v4 (bool): [optional] when True enables signature_version=s3v4 which is required for SSE
                         protected buckets/objects
            profile_name (str): [optional] credential profile to use, defaults to None
        Returns:
            class: boto3 client
        """
        if not aws_access_key_id and not profile_name:
            self.logger.debug(
                "no explicit keys or profile for this client, fetching the credentials from the %s set" % credential_set)
            if credential_set not in self._credential_sets.keys():
                raise KeyError('credential set %s does not exist' % credential_set)
            aws_access_key_id, aws_secret_access_key, aws_session_token, profile_name = self._credential_sets[
                credential_set]
        if not region:
            self.logger.debug("Region not set explicitly, getting default region")
            region = os.environ['AWS_DEFAULT_REGION']
        s3v4 = 's3v4' if s3v4 else 'default_sig_version'
        try:
            self.logger.debug("Trying to get [%s][%s][%s][%s]" % (credential_set, region, service, s3v4))
            client = self._clients[credential_set][region][service][s3v4]
            if aws_access_key_id:
                if self._clients[credential_set][region]['session'].get_credentials().access_key != aws_access_key_id:
                    self.logger.debug("credentials changed, forcing update...")
                    raise KeyError("New credentials for this credential_set, need a new session.")
            return client
        except KeyError:
            self.logger.debug("Couldn't return an existing client, making a new one...")
            if credential_set not in self._clients.keys():
                self._clients[credential_set] = {}
            if region not in self._clients[credential_set].keys():
                self._clients[credential_set][region] = {}
            if service not in self._clients[credential_set].keys():
                self._clients[credential_set][region][service] = {}
            if 'session' not in self._clients[credential_set][region].keys():
                self._clients[credential_set][region]['session'] = self._create_session(
                    region, aws_access_key_id, aws_secret_access_key, aws_session_token, profile_name
                )
            self._clients[credential_set][region][service][s3v4] = self._create_client(
                credential_set, region, service, s3v4
            )
            return self._clients[credential_set][region][service][s3v4]

    def _create_session(self, region, access_key, secret_key, session_token, profile_name):
        """creates a boto3 session object

        Args:
            region (str): region name
            access_key (str): [optional] IAM secret key, defaults to None
            secret_key (str): [optional] IAM secret key, defaults to None
            session_token (str): [optional] IAM secret key, defaults to None
            profile_name (str): [optional] credential profile to use, defaults to None
        """
        session = None
        retry = 0
        max_retries = 4
        while not session:
            try:
                with self._lock:
                    if access_key and secret_key and session_token:
                        session = boto3.session.Session(
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key,
                            aws_session_token=session_token,
                            region_name=region
                        )
                    elif access_key and secret_key:
                        session = boto3.session.Session(
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key,
                            region_name=region
                        )
                    elif profile_name:
                        session = boto3.session.Session(
                            profile_name=profile_name,
                            region_name=region
                        )
                    else:
                        session = boto3.session.Session(region_name=region)
                return session
            except Exception as e:
                if "could not be found" in str(e):
                    raise
                self.logger.debug("failed to create session", exc_info=1)
                retry += 1
                if retry >= max_retries:
                    raise
                sleep(5 * (retry ** 2))

    def _create_client(self, credential_set, region, service, s3v4):
        """creates (or fetches from cache) a boto3 client object

        Args:
            credential_set (str): session name
            region (str): region name
            service (str): AWS service name
            s3v4 (bool): when True enables signature_version=s3v4 which is required for SSE protected buckets/objects
        """
        client = None
        retry = 0
        max_retries = 4
        while not client:
            try:
                with self._lock:
                    if s3v4 == 's3v4':
                        client = self._clients[credential_set][region]['session'].client(
                            service,
                            config=botocore.client.Config(signature_version='s3v4')
                        )
                    else:
                        client = self._clients[credential_set][region]['session'].client(service)
                return client
            except Exception:
                self.logger.debug("failed to create client", exc_info=1)
                retry += 1
                if retry >= max_retries:
                    raise
                sleep(5 * (retry ** 2))

    def get_available_regions(self, service):
        """fetches available regions for a service

        Args:
            service (str): AWS service name

        Returns:
            list: aws region name strings
        """

        for credential_set in self._clients.keys():
            for region in self._clients[credential_set].keys():
                if 'session' in self._clients[credential_set][region].keys():
                    return self._clients[credential_set][region]['session'].get_available_regions(service)
        session = boto3.session.Session()
        return session.get_available_regions(service)

    def get_session(self, credential_set, region=None):
        """fetches existing session for credential set in a region

        Args:
            credential_set (str): name of credential set from a previously created client
            region (str): region name, defaults to current region

        Returns:
            boto3.session.Session: instance of boto3 Session object
        """
        if not region:
            self.logger.debug("Region not set explicitly, getting default region")
            region = os.environ['AWS_DEFAULT_REGION']

        return self._clients[credential_set][region]['session']


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
        except Exception:
            pass
        try:
            metadata["message"] = message
            return json.dumps(metadata)
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

        return yaml.load(stream, OrderedSafeLoader)

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

        yaml_dump = yaml.dump(data, stream, OrderedSafeDumper, **kwds)

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
