#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago.cardenas@outlook.com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
#
# repo: https://github.com/aws-quickstart/taskcat
# docs: https://aws-quickstart.github.io/taskcat/
#
# This program takes as input:
# CloudFormation template and json formatted parameter input file
# To create tests define the test params in config.yml (Example below)
# Planned Features:
# - Email test results to owner of project

# --imports --
from __future__ import print_function

import datetime
import json
import os
import re
import time
import uuid
import boto3
import yaml
import cfnlint.core
import textwrap
import base64
import logging
from botocore.vendored import requests

from taskcat.reaper import Reaper
from taskcat.client_factory import ClientFactory
from taskcat.logger import PrintMsg
from taskcat.generate_reports import ReportBuilder
from taskcat.common_utils import CommonTools
from taskcat.cfn_logutils import CfnLogTools
from taskcat.cfn_resources import CfnResourceTools
from taskcat.exceptions import TaskCatException
from taskcat.s3_sync import S3Sync
from taskcat.common_utils import exit0, exit1, param_list_to_dict
from taskcat.legacy_cli import get_installed_version
from taskcat.template_params import ParamGen


class TestData(object):
    """
        This class is used to represent the test data.
    """
    def __init__(self):
        self.__test_name = None
        self.__test_stacks = []

    def set_test_name(self, name):
        self.__test_name = name

    def get_test_name(self):
        return self.__test_name

    def get_test_stacks(self):
        return self.__test_stacks

    def add_test_stack(self, stack):
        self.__test_stacks.append(stack)


"""
    Task(Cat = CloudFormation Automated Testing)

    This is the main TaskCat class, which provides various functions to
    perform testing of CloudFormation templates in multiple regions and
    generate report.
"""


log = logging.getLogger(__name__)


# This class should be split into smaller components, and entirely replaced by v9 stable release
class LegacyTaskCat(object):
    # CONSTRUCTOR
    # ============

    def __init__(self, args, nametag='[taskcat]'):
        self.nametag = '{1}{0}{2}'.format(nametag, PrintMsg.name_color, PrintMsg.rst_color)
        self._project_name = None
        self._project_path = None
        self.owner = None
        self.banner = None
        self.capabilities = []
        self.config = 'taskcat.yml'
        self.test_region = []
        self.s3bucket = None
        self.s3bucket_type = None
        self.template_path = None
        self.parameter_path = None
        self.default_region = None
        self._template_file = None
        self._template_type = None
        self._parameter_file = None
        self._parameter_path = None
        self.ddb_table = None
        self._enable_dynamodb = False
        self._termsize = 110
        self._strict_syntax_json = True
        self._banner = ""
        self._auth_mode = None
        self._report = False
        self._use_global = False
        self._parameters = {}
        self.run_cleanup = True
        self.public_s3_bucket = False
        self._aws_access_key = None
        self._aws_secret_key = None
        self._boto_profile = None
        self._boto_client = ClientFactory()
        self._key_url_map = {}
        self.retain_if_failed = False
        self.tags = []
        self.stack_prefix = ''
        self.template_data = None
        self.version = get_installed_version()
        self.s3_url_prefix = ""
        self.upload_only = False
        self._max_bucket_name_length = 63
        self.lambda_build_only = False
        self._sig = base64.b64decode("dENhVA==").decode()
        self._jobid = str(uuid.uuid4())

        if args.upload_only:
            self.upload_only = True

        if args.lambda_build_only:
            self.lambda_build_only = True

        if args.enable_sig_v2:
            self.enable_sig_v2 = True

        try:
            self.tags = args.tags
        except AttributeError:
            pass

        if not re.compile('^[a-z0-9\-]+$').match(args.stack_prefix):
            raise TaskCatException("--stack-prefix only accepts lowercase letters, numbers and '-'")
        self.stack_prefix = args.stack_prefix

        self.verbosity = args.verbosity

        # Overrides Defaults for cleanup but does not overwrite config.yml
        if args.no_cleanup:
            self.run_cleanup = False

        try:
            if args.exclude is not None:
                self.exclude = args.exclude
        except AttributeError:
            ## TODO: Figure out why we're swallowing an exception with 0 feedback here
            pass

        if args.public_s3_bucket:
            self.public_s3_bucket = True

        if args.no_cleanup_failed:
            self.retain_if_failed = True
        self.one_or_more_tests_failed = False
        self.exclude = []
        self.enable_sig_v2 = False

    # SETTERS ANPrintMsg.DEBUG GETTERS
    # ===================

    def set_project_name(self, project_name):
        self._project_name = project_name

    def get_project_name(self):
        return self._project_name

    def get_project_path(self):
        return self._project_path

    def set_project_path(self, path):
        self._project_path = path

    def set_owner(self, owner):
        self.owner = owner

    def get_owner(self):
        return self.owner

    def set_capabilities(self, ability):
        self.capabilities.append(ability)

    def get_capabilities(self):
        return self.capabilities

    def set_s3bucket(self, bucket):
        self.s3bucket = bucket

    def get_s3bucket(self):
        return str(self.s3bucket)

    def set_s3bucket_type(self, bucket):
        self.s3bucket_type = bucket

    def get_s3bucket_type(self):
        return str(self.s3bucket_type)

    def set_config(self, config_yml):
        if os.path.isfile(config_yml):
            self.config = config_yml
        else:
            exit1("Cannot locate file %s" % config_yml)

    def get_config(self):
        return self.config

    def get_strict_syntax_json(self):
        return self._strict_syntax_json

    def set_strict_syntax_json(self, value):
        self._strict_syntax_json = value

    def get_template_file(self):
        return self._template_file

    def set_template_file(self, template):
        self._template_file = template

    def get_template_type(self):
        return self._template_type

    def set_template_type(self, template_type):
        self._template_type = template_type

    def set_parameter_file(self, parameter):
        self._parameter_file = parameter

    def get_exclude(self):
        return self.exclude

    def get_parameter_file(self):
        return self._parameter_file

    def set_parameter_path(self, parameter):
        self.parameter_path = parameter

    def get_parameter_path(self):
        return self.parameter_path

    def get_param_includes(self, original_keys):
        """
        This function searches for ~/.aws/taskcat_global_override.json,
        then <project>/ci/taskcat_project_override.json, in that order.
        Keys defined in either of these files will override Keys defined in <project>/ci/*.json or in the template parameters.

        :param original_keys: json object derived from Parameter Input JSON in <project>/ci/
        """
        # Github/issue/57
        # Look for ~/.taskcat_overrides.json

        log.info("|Processing Overrides")
        # Fetch overrides Home dir first.
        dict_squash_list = []
        _homedir_override_file_path = "{}/.aws/{}".format(os.path.expanduser('~'), 'taskcat_global_override.json')
        if os.path.isfile(_homedir_override_file_path):
            with open(_homedir_override_file_path) as f:
                try:
                    _homedir_override_json = json.loads(f.read())
                except ValueError:
                    raise TaskCatException("Unable to parse JSON (taskcat global overrides)")
                log.debug("Values loaded from ~/.aws/taskcat_global_override.json")
                log.debug(str(_homedir_override_json))
            dict_squash_list.append(_homedir_override_json)

        # Now look for per-project override uploaded to S3.
        local_override_file_path = "{}/ci/taskcat_project_override.json".format(self.get_project_path())
        try:
            # Intentional duplication of self.get_content() here, as I don't want to break that due to
            # tweaks necessary here.
            with open(local_override_file_path, 'r') as f:
                content = f.read()
            _obj = json.loads(content)
            dict_squash_list.append(_obj)
            log.debug("Values loaded from {}".format(local_override_file_path))
            log.debug(str(_obj))
        except ValueError:
            raise TaskCatException("Unable to parse JSON (taskcat project overrides)")
        except TaskCatException:
            raise
        except Exception as e:
            pass

        param_index = param_list_to_dict(original_keys)

        template_params = self.extract_template_parameters()
        # Merge the two lists, overriding the original values if necessary.
        for override in dict_squash_list:
            for override_pd in override:
                key = override_pd['ParameterKey']
                if key in param_index.keys():
                    idx = param_index[key]
                    original_keys[idx] = override_pd
                else:
                    log.info("Cannot apply overrides for the [{}] Parameter. You did not include this parameter in [{}]".format(key, self.get_parameter_file()))

        # check if s3 bucket and QSS3BucketName param match. fix if they dont.
        bucket_name = self.get_s3bucket()
        _kn = 'QSS3BucketName'
        if _kn in self.extract_template_parameters():
            if _kn in param_index:
                _knidx = param_index[_kn]
                param_bucket_name = original_keys[_knidx]['ParameterValue']
                if param_bucket_name != bucket_name and param_bucket_name != '$[taskcat_autobucket]':
                    log.info("Inconsistency detected between S3 Bucket Name provided in the TaskCat Config [{}] and QSS3BucketName Parameter Value within the template: [{}]".format(
                             bucket_name, param_bucket_name))
                    log.info("Setting the value of QSS3BucketName to [{}]".format(bucket_name))
                    original_keys[_knidx]['ParameterValue'] = bucket_name

        return original_keys

    def set_template_path(self, template):
        self.template_path = template

    def get_template_path(self):
        return self.template_path

    def set_parameter(self, key, val):
        self._parameters[key] = val

    def get_parameter(self, key):
        return self._parameters[key]

    def set_dynamodb_table(self, ddb_table):
        self.ddb_table = ddb_table

    def get_dynamodb_table(self):
        return self.ddbtable

    def set_default_region(self, region):
        self.default_region = region

    def get_default_region(self):
        return self.default_region

    def get_test_region(self):
        return self.test_region

    def set_test_region(self, region_list):
        self.test_region = []
        for region in region_list:
            self.test_region.append(region)

    def set_docleanup(self, cleanup_value):
        self.run_cleanup = cleanup_value

    def get_docleanup(self):
        return self.run_cleanup

    #      FUNCTIONS       #
    # ==================== #

    def stage_in_s3(self, taskcat_cfg):
        """
        Upload templates and other artifacts to s3.

        This function creates the s3 bucket with name provided in the config yml file. If
        no bucket name provided, it creates the s3 bucket using project name provided in
        config yml file. And uploads the templates and other artifacts to the s3 bucket.

        :param taskcat_cfg: Taskcat configuration provided in yml file

        """
        if self.public_s3_bucket:
            bucket_or_object_acl = 'public-read'
        else:
            bucket_or_object_acl = 'bucket-owner-read'
        s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)

        if 's3bucket' in taskcat_cfg['global'].keys():
            self.set_s3bucket(taskcat_cfg['global']['s3bucket'])
            self.set_s3bucket_type('defined')
            log.info("Staging Bucket => " + self.get_s3bucket())
            if len(self.get_s3bucket()) > self._max_bucket_name_length:
                raise TaskCatException("The bucket name you provided is greater than {} characters.".format(self._max_bucket_name_length))
            try:
                _ = s3_client.list_objects(Bucket=self.get_s3bucket())
            except s3_client.exceptions.NoSuchBucket:
                raise TaskCatException("The bucket you provided [{}] does not exist. Exiting.".format(self.get_s3bucket()))
            except Exception:
                raise
        else:
            auto_bucket = 'taskcat-' + self.stack_prefix + '-' + self.get_project_name() + "-" + self._jobid[:8]
            auto_bucket = auto_bucket.lower()
            if len(auto_bucket) > self._max_bucket_name_length:
                auto_bucket = auto_bucket[:self._max_bucket_name_length]
            if self.get_default_region():
                log.info('Creating bucket {0} in {1}'.format(auto_bucket, self.get_default_region()))
                if self.get_default_region() == 'us-east-1':
                    response = s3_client.create_bucket(ACL=bucket_or_object_acl,
                                                       Bucket=auto_bucket)
                else:
                    response = s3_client.create_bucket(ACL=bucket_or_object_acl,
                                                       Bucket=auto_bucket,
                                                       CreateBucketConfiguration={
                                                           'LocationConstraint': self.get_default_region()
                                                       })

                self.set_s3bucket_type('auto')
            else:
                raise TaskCatException("Default_region = " + self.get_default_region())

            if response['ResponseMetadata']['HTTPStatusCode'] is 200:
                log.info("Staging Bucket => [%s]" % auto_bucket)
                self.set_s3bucket(auto_bucket)
            else:
                log.info('Creating bucket {0} in {1}'.format(auto_bucket, self.get_default_region()))
                response = s3_client.create_bucket(ACL=bucket_or_object_acl,
                                                   Bucket=auto_bucket,
                                                   CreateBucketConfiguration={
                                                       'LocationConstraint': self.get_default_region()})

                if response['ResponseMetadata']['HTTPStatusCode'] is 200:
                    log.info("Staging Bucket => [%s]" % auto_bucket)
                    self.set_s3bucket(auto_bucket)
            if self.tags:
                s3_client.put_bucket_tagging(
                    Bucket=auto_bucket,
                    Tagging={"TagSet": self.tags}
                )
            if not self.enable_sig_v2:
                print(PrintMsg.INFO + "Enforcing sigv4 requests for bucket %s" % auto_bucket)
                policy = """{
   "Version": "2012-10-17",
   "Statement": [
         {
               "Sid": "Test",
               "Effect": "Deny",
               "Principal": "*",
               "Action": "s3:*",
               "Resource": "arn:aws:s3:::%s/*",
               "Condition": {
                     "StringEquals": {
                           "s3:signatureversion": "AWS"
                     }
               }
         }
   ]
}
""" % auto_bucket
                s3_client.put_bucket_policy(Bucket=auto_bucket, Policy=policy)

        for exclude in self.get_exclude():
            if os.path.isdir(exclude):
                S3Sync.exclude_path_prefixes.append(exclude)
            else:
                S3Sync.exclude_files.append(exclude)

        S3Sync(s3_client, self.get_s3bucket(), self.get_project_name(), self.get_project_path(), bucket_or_object_acl)
        self.s3_url_prefix = "https://" + self.get_s3_hostname() + "/" + self.get_project_name()
        if self.upload_only:
            exit0("Upload completed successfully")

    def get_available_azs(self, region, count):
        """
        Returns a list of availability zones in a given region.

        :param region: Region for the availability zones
        :param count: Minimum number of availability zones needed

        :return: List of availability zones in a given region

        """
        available_azs = []
        ec2_client = self._boto_client.get('ec2', region=region)
        availability_zones = ec2_client.describe_availability_zones(
            Filters=[{'Name': 'state', 'Values': ['available']}])

        for az in availability_zones['AvailabilityZones']:
            available_azs.append(az['ZoneName'])

        if len(available_azs) < count:
            exit1("Only {0} az's are available in {1}".format(len(available_azs), region))
        else:
            azs = ','.join(available_azs[:count])
            return azs

    def remove_public_acl_from_bucket(self):
        if self.public_s3_bucket:
            log.info('The staging bucket [{}] should be only required during cfn bootstrapping. Removing public '
                        'permission as they are no longer needed!'.format(self.s3bucket))
            s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)
            s3_client.put_bucket_acl(Bucket=self.s3bucket, ACL='private')

    def get_content(self, bucket, object_key):
        """
        Returns the content of an object, given the bucket name and the key of the object

        :param bucket: Bucket name
        :param object_key: Key of the object

        :return: Content of the object

        """
        s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)
        try:
            dict_object = s3_client.get_object(Bucket=bucket, Key=object_key)
        except TaskCatException:
            raise
        except Exception:
            log.error("Attempted to fetch Bucket: {}, Key: {}".format(bucket, object_key))
            raise
        content = dict_object['Body'].read().decode('utf-8').strip()
        return content

    def get_s3contents(self, url):
        """
        Returns S3 object.
        - If --public-s3-bucket is passed, returns via the requests library.
        - If not, does an S3 API call.

        :param url: URL of the S3 object to return.
        :return: Data of the s3 object
        """
        if self.public_s3_bucket:
            payload = requests.get(url)
            return payload.text
        key = self._key_url_map[url]
        return self.get_content(self.get_s3bucket(), key)

    def get_contents(self, path):
        """
        Returns local file contents as a string.

        :param path: URL of the S3 object to return.
        :return: file contents
        """
        with open(path, 'r') as f:
            data = f.read()
        return data

    def get_s3_hostname(self):
        """
        Returns S3 hostname of target bucket
        :return: S3 hostname

        """
        s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)
        bucket_location = s3_client.get_bucket_location(Bucket=self.get_s3bucket())
        if bucket_location['LocationConstraint'] is not None:
            hostname = "s3-{0}.{1}/{2}".format(bucket_location['LocationConstraint'], "amazonaws.com",
                                               self.get_s3bucket())
        else:
            hostname = "{0}.s3.amazonaws.com".format(self.get_s3bucket())
        return hostname

    def get_global_region(self, yamlcfg):
        """
        Returns a list of regions defined under global region in the yml config file.

        :param yamlcfg: Content of the yml config file
        :return: List of regions

        """
        g_regions = []
        for keys in yamlcfg['global'].keys():
            if 'region' in keys:
                namespace = 'global'
                try:
                    iter(yamlcfg['global']['regions'])
                    for region in yamlcfg['global']['regions']:
                        g_regions.append(region)
                        self._use_global = True
                except TypeError as e:
                    log.error("No regions defined in [%s]:" % namespace)
                    log.error("Please correct region defs[%s]:" % namespace)
        return g_regions

    def extract_template_parameters(self):
        """
        Returns a dictionary of the parameters in the template entrypoint, if it exist.
        Otherwise, return empty {} dictionary if there are no parameters in the template.

        :return: list of parameters for the template.
        """
        if 'Parameters' in self.template_data:
            return self.template_data['Parameters'].keys()
        else:
            return {}

    def validate_template(self, taskcat_cfg, test_list):
        """
        Returns TRUE if all the template files are valid, otherwise FALSE.

        :param taskcat_cfg: TaskCat config object
        :param test_list: List of tests

        :return: TRUE if templates are valid, else FALSE
        """
        # Load global regions
        self.set_test_region(self.get_global_region(taskcat_cfg))
        for test in test_list:
            log.info(" :Validate Template in test[%s]" % test, extra={"nametag": self.nametag})
            self.define_tests(taskcat_cfg, test)
            try:
                log.debug("Default region [%s]" % self.get_default_region())
                cfn = self._boto_client.get('cloudformation', region=self.get_default_region())

                result = cfn.validate_template(TemplateURL=self.s3_url_prefix + '/templates/' + self.get_template_file())
                log.warning("Validated [%s]" % self.get_template_file(), extra={"nametag": PrintMsg.PASS})
                if 'Description' in result:
                    cfn_result = (result['Description'])
                    log.info("Description  [%s]" % textwrap.fill(cfn_result))
                else:
                    log.warning("Please include a top-level description for template: [%s]" % self.get_template_file())
                cfn_params = json.dumps(result['Parameters'], indent=11, separators=(',', ': '))
                log.debug("Parameters:")
                log.debug(cfn_params)
            except TaskCatException:
                raise
            except Exception as e:
                log.debug(str(e))
                log.info("Deleting any automatically-created buckets...")
                self.delete_autobucket()
                raise TaskCatException("Cannot validate %s" % self.get_template_file())
        return True

    def generate_input_param_values(self, s_parms, region):
        """
        Given a cloudformation input parameter file as JSON, this function generates the values
        for the parameters indicated by $[] appropriately, replaces $[] with new value and return
        the updated JSON.

        :param region:
        :param s_parms: Cloudformation template input parameter file as JSON

        :return: Input parameter file as JSON with $[] replaced with generated values

        """
        # gentype = None

        # Auto-generated stack inputs

        # (Passwords)
        # Value that matches the following pattern will be replaced
        # - Parameters must start with $[
        # - Parameters must end with ]
        # - genpass in invoked when _genpass_X is found
        # - X is length of the string
        # Example: $[taskcat_genpass_8]
        # Optionally - you can specify the type of password by adding
        # - A alpha-numeric passwords
        # - S passwords with special characters
        # Example: $[taskcat_genpass_8A]
        # Generates: tI8zN3iX8
        # or
        # Example: $[taskcat_genpass_8S]
        # Generates: mA5@cB5!

        # (Auto generated s3 bucket )
        # Example: $[taskcat_autobucket]
        # Generates: <evaluates to auto generated bucket name>

        # (Generate UUIPrintMsg.DEBUG String)
        # Example: $[taskcat_genuuid]
        # Generates: 1c2e3483-2c99-45bb-801d-8af68a3b907b

        # (Generate Random String)
        # Example: $[taskcat_random-string]
        # Generates: yysuawpwubvotiqgwjcu
        # or
        # Example: $[taskcat_random-numbers]
        # Generates: 56188163597280820763

        # (Availability Zones)
        # Value that matches the following pattern will be replaced
        # - Parameters must start with $[
        # - Parameters must end with ]
        # - genaz in invoked when _genaz_X is found
        # - A number of AZ's will be selected from the region
        #   the stack is attempting to launch
        # Example: $[taskcat_genaz_2] (if the region is us-east-2)
        # Generates: us-east-1a, us-east-2b

        # (Retrieve previously generated value)
        # Example: $[taskcat_getval_KeyName]
        # UseCase: Can be used to confirm generated passwords

        # (Presigned URLs)
        # Usage: $[taskcat_presignedurl],S3BucketName,PathToKey,[Optional URL Expiry in seconds]
        #
        # Example with default expiry (1 hour):
        # - $[taskcat_presignedurl],my-example-bucket,example/content.txt
        #
        # Example with 5 minute expiry:
        # - $[taskcat_presignedurl],my-example-bucket,example/content.txt,300

        return ParamGen(param_list=s_parms, bucket_name=self.get_s3bucket(), boto_client=self._boto_client, region=region).results

    def stackcreate(self, taskcat_cfg, test_list, sprefix):
        """
        This function creates CloudFormation stack for the given tests.

        :param taskcat_cfg: TaskCat config as yaml object
        :param test_list: List of tests
        :param sprefix: Special prefix as string. Purpose of this param is to use it for tagging
            the stack.

        :return: List of TestData objects

        """
        testdata_list = []
        self.set_capabilities('CAPABILITY_AUTO_EXPAND')
        self.set_capabilities('CAPABILITY_NAMED_IAM')
        for test in test_list:
            testdata = TestData()
            testdata.set_test_name(test)
            log.info("{0}|PREPARING TO LAUNCH => {1}{2}".format(PrintMsg.header, test, PrintMsg.rst_color))
            sname = str(self._sig)

            stackname = sname + '-' + sprefix + '-' + test + '-' + self._jobid[:8]
            self.define_tests(taskcat_cfg, test)
            for region in self.get_test_region():
                log.info("Preparing to launch in region [%s] " % region)
                try:
                    cfn = self._boto_client.get('cloudformation', region=region)
                    s_parmsdata = self.get_contents(self.get_project_path() + "/ci/" + self.get_parameter_file())
                    s_parms = json.loads(s_parmsdata)
                    s_include_params = self.get_param_includes(s_parms)
                    if s_include_params:
                        s_parms = s_include_params
                    j_params = self.generate_input_param_values(s_parms, region)
                    log.debug("Creating Boto Connection region=%s" % region)
                    log.debug("StackName=" + stackname)
                    log.debug("DisableRollback=True")
                    log.debug("TemplateURL=%s" % self.get_template_path())
                    log.debug("Capabilities=%s" % self.get_capabilities())
                    log.debug("Parameters:")
                    log.debug("Tags:%s" % str(self.tags))
                    if self.get_template_type() == 'json':
                        log.debug(json.dumps(j_params, sort_keys=True, indent=11, separators=(',', ': ')))
                    try:
                        stackdata = cfn.create_stack(
                            StackName=stackname,
                            DisableRollback=True,
                            TemplateURL=self.get_template_path(),
                            Parameters=j_params,
                            Capabilities=self.get_capabilities(),
                            Tags=self.tags
                        )
                        log.info("|CFN Execution mode [create_stack]")
                    except cfn.exceptions.ClientError as e:
                        if not str(e).endswith('cannot be used with templates containing Transforms.'):
                            raise
                        log.info("|CFN Execution mode [change_set]")
                        stack_cs_data = cfn.create_change_set(
                            StackName=stackname,
                            TemplateURL=self.get_template_path(),
                            Parameters=j_params,
                            Capabilities=self.get_capabilities(),
                            ChangeSetType="CREATE",
                            ChangeSetName=stackname + "-cs"
                        )
                        change_set_name = stack_cs_data['Id']

                        # wait for change set
                        waiter = cfn.get_waiter('change_set_create_complete')
                        waiter.wait(
                            ChangeSetName=change_set_name,
                            WaiterConfig={
                                'Delay': 10,
                                'MaxAttempts': 26  # max lambda execute is 5 minutes
                            })

                        cfn.execute_change_set(
                            ChangeSetName=change_set_name
                        )

                        stackdata = {
                            'StackId': stack_cs_data['StackId']
                        }

                    testdata.add_test_stack(stackdata)
                except TaskCatException:
                    raise
                except Exception as e:
                    log.debug(str(e))
                    raise TaskCatException("Cannot launch %s" % self.get_template_file())

            testdata_list.append(testdata)
        for test in testdata_list:
            for stack in test.get_test_stacks():
                log.info(" |{}LAUNCHING STACKS{}".format(PrintMsg.header, PrintMsg.rst_color), extra={"nametag": self.nametag})
                log.info("{}{} {} {}".format(
                    PrintMsg.header,
                    test.get_test_name(),
                    str(stack['StackId']).split(':stack', 1),
                    PrintMsg.rst_color), extra={"nametag": ""})
        return testdata_list

    def validate_parameters(self, taskcat_cfg, test_list):
        """
        This function validates the parameters file of the CloudFormation template.

        :param taskcat_cfg: TaskCat config yaml object
        :param test_list: List of tests

        :return: TRUPrintMsg.ERROR if the parameters file is valid, else FALSE
        """
        for test in test_list:
            self.define_tests(taskcat_cfg, test)
            log.info(" |Validate JSON input in test[%s]" % test, extra={"nametag": self.nametag})
            log.debug("parameter_path = %s" % self.get_parameter_path())

            inputparms = self.get_contents(self.get_project_path() + "/ci/" + self.get_parameter_file())

            jsonstatus = self.check_json(inputparms)

            log.debug("jsonstatus = %s" % jsonstatus)

            if jsonstatus:
                log.warning("Validated [%s]" % self.get_parameter_file(), extra={"nametag": PrintMsg.PASS})
            else:
                log.debug("parameter_file = %s" % self.get_parameter_file())
                raise TaskCatException("Cannot validate %s" % self.get_parameter_file())
        return True

    @staticmethod
    def regxfind(re_object, data_line):
        """
        Returns the matching string.

        :param re_object: Regex object
        :param data_line: String to be searched

        :return: Matching String if found, otherwise return 'Not-found'
        """
        sg = re_object.search(data_line)
        if sg:
            return str(sg.group())
        else:
            return str('Not-found')


    def stackcheck(self, stack_id):
        """
        Given the stack id, this function returns the status of the stack as
        a list with stack name, region, and status as list items, in the respective
        order.

        :param stack_id: CloudFormation stack id

        :return: List containing the stack name, region and stack status in the
            respective order.
        """
        stackdata = CommonTools(stack_id).parse_stack_info()
        region = stackdata['region']
        stack_name = stackdata['stack_name']
        test_info = []

        cfn = self._boto_client.get('cloudformation', region=region)
        # noinspection PyBroadException
        try:
            test_query = (cfn.describe_stacks(StackName=stack_name))
            for result in test_query['Stacks']:
                test_info.append(stack_name)
                test_info.append(region)
                test_info.append(result.get('StackStatus'))
                if result.get(
                        'StackStatus') == 'CREATE_IN_PROGRESS' or result.get('StackStatus') == 'DELETE_IN_PROGRESS':
                    test_info.append(1)
                else:
                    test_info.append(0)
        except TaskCatException:
            raise
        except Exception:
            test_info.append(stack_name)
            test_info.append(region)
            test_info.append("STACK_DELETED")
            test_info.append(0)
        return test_info

    def db_initproject(self, table_name):
        """
        :param table_name: Creates table if it does not exist. Waits for the table to become available
        :return: DynamoDB object
        """
        dynamodb = boto3.resource('dynamodb', region_name=self.get_default_region())
        try:
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'job-name',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'job-name',
                        'AttributeType': 'S'
                    }

                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5,
                }
            )
            log.info('Creating new [{}]'.format(table_name))
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            return table
        except TaskCatException:
            raise
        except Exception as notable:
            if notable:
                log.info('Adding to existing [{}]'.format(table_name))
                table = dynamodb.Table(table_name)
                table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
                return table

    def db_item(self, table, time_stamp, region, job_name, log_group, owner, job_status):
        # :TODO add jobid getter and setter
        table.put_item(
            Item={
                'job-name': job_name,
                'last-run': time_stamp,
                'region': region,
                'owner': owner,
                'test-history': log_group,
                'job-status': job_status,
                'test-outputs': self._jobid[:8],
            }
        )

    def enable_dynamodb_reporting(self, enable):
        self._enable_dynamodb = enable

    def get_stackstatus(self, testdata_list, speed):
        """
        Given a list of TestData objects, this function checks the stack status
        of each CloudFormation stack and updates the corresponding TestData object
        with the status.

        :param testdata_list: List of TestData object
        :param speed: Interval (in seconds) in which the status has to be checked in loop

        """
        active_tests = 1
        log.warning("{}{} {} [{}]{}".format(
            PrintMsg.header,
            'AWS REGION'.ljust(15),
            'CLOUDFORMATION STACK STATUS'.ljust(26),
            'CLOUDFORMATION STACK NAME',
            PrintMsg.rst_color))
        latest_log = {}
        while active_tests > 0:
            current_active_tests = 0
            time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for test in testdata_list:
                if test not in latest_log.keys():
                    latest_log[test] = {}
                for stack in test.get_test_stacks():
                    stack_id = stack['StackId']
                    if stack_id not in latest_log[test].keys():
                        latest_log[test][stack_id] = ""
                    stackquery = self.stackcheck(str(stack['StackId']))
                    current_active_tests = stackquery[3] + current_active_tests
                    logs = ("{3}{0} {1} [{2}]{4}".format(
                        stackquery[1].ljust(15),
                        stackquery[2].ljust(26),
                        stackquery[0],
                        PrintMsg.highlight,
                        PrintMsg.rst_color))
                    if logs != latest_log[test][stack_id]:
                        log.warning(logs)
                    else:
                        log.info(logs)
                    latest_log[test][stack_id] = logs
                    if self._enable_dynamodb:
                        table = self.db_initproject(self.get_project_name())
                        # Do not update when in cleanup start (preserves previous status)
                        skip_status = ['DELETE_IN_PROGRESS', 'STACK_DELETED']
                        if stackquery[2] not in skip_status:
                            self.db_item(table,
                                         time_stamp,
                                         stackquery[1],
                                         test.get_test_name(),
                                         'log group stub',
                                         self.get_owner(),
                                         stackquery[2])

                    stack['status'] = stackquery[2]
                    active_tests = current_active_tests
                    time.sleep(speed)

    def cleanup(self, testdata_list, speed):
        """
        This function deletes the CloudFormation stacks of the given tests.

        :param testdata_list: List of TestData objects
        :param speed: Interval (in seconds) in which the status has to be checked
            while deleting the stacks.

        """
        self.remove_public_acl_from_bucket()

        docleanup = self.get_docleanup()
        log.debug("clean-up = %s " % str(docleanup))

        if docleanup:
            log.warning(" |CLEANUP STACKS{}".format(PrintMsg.header, PrintMsg.rst_color), extra={"nametag": self.nametag})
            self.stackdelete(testdata_list)
            self.get_stackstatus(testdata_list, speed)
            self.deep_cleanup(testdata_list)
        else:
            log.info("[Retaining Stacks (Cleanup is set to {0}]".format(docleanup))

    def deep_cleanup(self, testdata_list):
        """
        This function deletes the AWS resources which were not deleted
        by deleting CloudFormation stacks.

        :param testdata_list: List of TestData objects

        """
        for test in testdata_list:
            failed_stack_ids = []
            for stack in test.get_test_stacks():
                if str(stack['status']) == 'DELETE_FAILED':
                    failed_stack_ids.append(stack['StackId'])
            if len(failed_stack_ids) == 0:
                log.info("All stacks deleted successfully. Deep clean-up not required.")
                continue

            log.info("Few stacks failed to delete. Collecting resources for deep clean-up.")
            # get test region from the stack id
            stackdata = CommonTools(failed_stack_ids[0]).parse_stack_info()
            region = stackdata['region']
            session = boto3.session.Session(region_name=region)
            s = Reaper(session)

            failed_stacks = CfnResourceTools(self._boto_client).get_all_resources(failed_stack_ids, region)
            # print all resources which failed to delete
            log.debug("Resources which failed to delete:\n")
            for failed_stack in failed_stacks:
                log.debug("Stack Id: " + failed_stack['stackId'])
                for res in failed_stack['resources']:
                    log.debug("{0} = {1}, {2} = {3}, {4} = {5}".format(
                        '\n\t\tLogicalId',
                        res.get('logicalId'),
                        '\n\t\tPhysicalId',
                        res.get('physicalId'),
                        '\n\t\tType',
                        res.get('resourceType')
                    ))
            s.delete_all(failed_stacks)

        self.delete_autobucket()

    def delete_autobucket(self):
        """
        This function deletes the automatically created S3 bucket(s) of the current project.
        """
        # Check to see if auto bucket was created
        if self.get_s3bucket_type() is 'auto':
            log.info("(Cleaning up staging assets)")

            s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)

            # Batch object processing by pages
            paginator = s3_client.get_paginator('list_objects')
            operation_parameters = {'Bucket': self.get_s3bucket(), 'Prefix': self.get_project_name()}
            s3_pages = paginator.paginate(**operation_parameters)

            # Load objects to delete
            objects_in_s3 = 1
            delete_keys = dict(Objects=[])
            try:
                for key in s3_pages.search('Contents'):
                    delete_keys['Objects'].append(dict(Key=key['Key']))
                    objects_in_s3 += 1
                    if objects_in_s3 == 1000:
                        # Batch delete 1000 objects at a time
                        s3_client.delete_objects(Bucket=self.get_s3bucket(), Delete=delete_keys)
                        log.info("Deleted {} objects from {}".format(objects_in_s3, self.get_s3bucket()))

                        delete_keys = dict(Objects=[])
                        objects_in_s3 = 1

                # Delete last batch of objects
                if objects_in_s3 > 1:
                    s3_client.delete_objects(Bucket=self.get_s3bucket(), Delete=delete_keys)
                    log.info("Deleted {} objects from {}".format(objects_in_s3, self.get_s3bucket()))

                # Delete bucket
                s3_client.delete_bucket(
                    Bucket=self.get_s3bucket())
                log.debug("Deleting Bucket {0}".format(self.get_s3bucket()))
            except s3_client.exceptions.NoSuchBucket:
                log.debug("Bucket {0} already deleted".format(self.get_s3bucket()))

        else:
            log.info("Retaining assets in s3bucket [{0}]".format(self.get_s3bucket()))

    def stackdelete(self, testdata_list):
        """
        This function deletes the CloudFormation stacks of the given tests.

        :param testdata_list: List of TestData objects

        """
        for test in testdata_list:
            for stack in test.get_test_stacks():
                stackdata = CommonTools(stack['StackId']).parse_stack_info()
                region = stackdata['region']
                stack_name = stackdata['stack_name']
                cfn = self._boto_client.get('cloudformation', region=region)
                cfn.delete_stack(StackName=stack_name)

    def define_tests(self, yamlc, test):
        """
        This function reads the given test config yaml object and defines
        the tests as per the given config object.

        :param yamlc: TaskCat config yaml object
        :param test: Test scenarios

        """
        for tdefs in yamlc['tests'].keys():
            if tdefs == test:
                t = yamlc['tests'][test]['template_file']
                p = yamlc['tests'][test]['parameter_input']
                n = yamlc['global']['qsname']
                o = yamlc['global']['owner']

                # Checks if cleanup flag is set
                # If cleanup is set to 'false' stack will not be deleted after
                # launch attempt
                if 'cleanup' in yamlc['global'].keys():
                    cleanupstack = yamlc['global']['cleanup']
                    if cleanupstack:
                        log.debug("cleanup set to yaml value")
                        self.set_docleanup(cleanupstack)
                    else:
                        log.info("Cleanup value set to (false)")
                        self.set_docleanup(False)
                else:
                    # By default do cleanup unless self.run_cleanup
                    # was overridden (set to False) by -n flag
                    if not self.run_cleanup:
                        log.debug("cleanup set by cli flag {0}".format(self.run_cleanup))
                    else:
                        self.set_docleanup(True)
                        log.info("No cleanup value set")
                        log.info(" - (Defaulting to cleanup)")

                # Load test setting
                self.set_owner(o)
                self.set_template_file(t)
                self.set_parameter_file(p)
                self.set_template_path(self.s3_url_prefix + '/templates/' + self.get_template_file())
                self.set_parameter_path(self.s3_url_prefix + '/ci/' + self.get_parameter_file())

                # Check to make sure template filenames are correct
                template_path = self.get_template_path()
                if not template_path:
                    log.error("Could not locate {0}".format(self.get_template_file()))
                    log.info("Check to make sure filename is correct?")
                    exit1()

                # Check to make sure parameter filenames are correct
                parameter_path = self.get_parameter_path()
                if not parameter_path:
                    log.error("Could not locate {0}".format(self.get_parameter_file()))
                    log.info("Check to make sure filename is correct?")
                    quit(1)

                # Detect template type

                cfntemplate = self.get_contents(self.get_project_path() + '/templates/' + self.get_template_file())

                if self.check_json(cfntemplate, quiet=True, strict=False):
                    self.set_template_type('json')
                    # Enforce strict json syntax
                    if self._strict_syntax_json:
                        self.check_json(cfntemplate, quiet=True, strict=True)
                    self.template_data = json.loads(cfntemplate)
                else:
                    self.set_template_type(None)
                    self.check_cfnyaml(cfntemplate, quiet=True, strict=False)
                    self.set_template_type('yaml')

                    m_constructor = cfnlint.decode.cfn_yaml.multi_constructor
                    loader = cfnlint.decode.cfn_yaml.MarkedLoader(cfntemplate, None)
                    loader.add_multi_constructor('!', m_constructor)
                    self.template_data = loader.get_single_data()

                log.info("|Acquiring tests assets for .......[%s]" % test)
                log.debug("|S3 Bucket     => [%s]" % self.get_s3bucket())
                log.debug("|Project       => [%s]" % self.get_project_name())
                log.debug("|Template      => [%s]" % self.get_template_path())
                log.debug("|Parameter     => [%s]" % self.get_parameter_path())
                log.debug("|TemplateType  => [%s]" % self.get_template_type())

                if 'regions' in yamlc['tests'][test]:
                    if yamlc['tests'][test]['regions'] is not None:
                        r = yamlc['tests'][test]['regions']
                        self.set_test_region(list(r))
                        msg = "|Defined Regions:\n"
                else:
                    global_regions = self.get_global_region(yamlc)
                    self.set_test_region(list(global_regions))
                    msg = "|Global Regions:"
                for list_o in self.get_test_region():
                    msg += "\t\t\t - [%s]\n" % list_o
                log.debug(msg)
                log.warning("(Completed) acquisition of [%s]\n" % test, extra={"nametag": PrintMsg.PASS})

    def check_json(self, jsonin, quiet=None, strict=None):
        """
        This function validates the given JSON.

        :param jsonin: Json object to be validated
        :param quiet: Optional value, if set True suppress verbose output
        :param strict: Optional value, Display errors and exit

        :return: TRUPrintMsg.ERROR if given Json is valid, FALSE otherwise.
        """
        try:
            parms = json.loads(jsonin)
            if not quiet:
                log.debug(json.dumps(parms, sort_keys=True, indent=11, separators=(',', ': ')))
        except ValueError as e:
            if strict:
                raise TaskCatException(str(e))
            return False
        return True

    def check_yaml(self, yamlin, quiet=None, strict=None):
        """
        This function validates the given YAML.

        :param yamlin: Yaml object to be validated
        :param quiet: Optional value, if set True suppress verbose output
        :param strict: Optional value, Display errors and exit

        :return: TRUPrintMsg.ERROR if given yaml is valid, FALSE otherwise.
        """
        try:
            parms = yaml.safe_load(yaml)
            if not quiet:
                log.debug(yaml.safe_dump(parms))
        except yaml.YAMLError as e:
            if strict:
                raise TaskCatException(str(e))
            return False
        return True

    def check_cfnyaml(self, yamlin, quiet=None, strict=None):
        """
        This function validates the given Cloudforamtion YAML.

        :param yamlin: CFNYaml object to be validated
        :param quiet: Optional value, if set True suppress verbose output
        :param strict: Optional value, Display errors and exit

        :return: TRUPrintMsg.ERROR if given yaml is valid, FALSE otherwise.
        """
        try:
            loader = cfnlint.decode.cfn_yaml.MarkedLoader(yamlin, None)
            loader.add_multi_constructor('!', cfnlint.decode.cfn_yaml.multi_constructor)
            if not quiet:
                log.debug(loader.get_single_data())
        except TaskCatException:
            raise
        except Exception as e:
            if strict:
                raise TaskCatException(str(e))
            return False
        return True

    # Set AWS Credentials
    # Set AWS Credentials
    def aws_api_init(self, args):
        """
        This function reads the AWS credentials from various sources to ensure
        that the client has right credentials defined to successfully run
        TaskCat against an AWS account.
        :param args: Command line arguments for AWS credentials. It could be
            either profile name, access key and secret key or none.
        """
        self.set_default_region(region=ClientFactory().get_default_region(args.aws_access_key, args.aws_secret_key, None, args.boto_profile))
        if args.boto_profile:
            self._auth_mode = 'profile'
            self._boto_profile = args.boto_profile
            try:
                sts_client = self._boto_client.get('sts',
                                                   profile_name=self._boto_profile,
                                                   region=self.get_default_region())
            except TaskCatException:
                raise
            except Exception as e:
                log.debug(str(e), exc_info=True)
                raise TaskCatException("Credential Error - Please check you profile!")
        elif args.aws_access_key and args.aws_secret_key:
            self._auth_mode = 'keys'
            self._aws_access_key = args.aws_access_key
            self._aws_secret_key = args.aws_secret_key
            try:
                sts_client = self._boto_client.get('sts',
                                                   aws_access_key_id=self._aws_access_key,
                                                   aws_secret_access_key=self._aws_secret_key,
                                                   region=self.get_default_region())
            except TaskCatException:
                raise
            except Exception as e:
                log.debug(str(e), exc_info=True)
                log.error("Credential Error - Please check you keys!")
        else:
            self._auth_mode = 'environment'
            try:
                sts_client = self._boto_client.get('sts', region=self.get_default_region())
            except TaskCatException:
                raise
            except Exception as e:
                log.debug(str(e), exc_info=True)
                raise TaskCatException("Credential Error - Please check your boto environment variable !")
        account = sts_client.get_caller_identity().get('Account')
        log.info(": AWS AccountNumber: \t [%s]" % account, extra={"nametag": self.nametag})
        log.info(": Authenticated via: \t [%s]" % self._auth_mode, extra={"nametag": self.nametag})

    def validate_yaml(self, yaml_file):
        """
        This function validates the given yaml file.

        :param yaml_file: Yaml file name

        """
        run_tests = []
        required_global_keys = [
            'qsname',
            'owner',
            'regions'
        ]

        required_test_parameters = [
            'template_file',
            'parameter_input'
        ]
        try:
            if os.path.isfile(yaml_file):
                log.info("Reading Config from: {0}".format(yaml_file), extra={"nametag": self.nametag})
                with open(yaml_file, 'r') as checkyaml:
                    cfg_yml = yaml.safe_load(checkyaml.read())
                    for key in required_global_keys:
                        if key in cfg_yml['global'].keys():
                            pass
                        else:
                            raise TaskCatException("global:%s missing from " % key + yaml_file)

                    for defined in cfg_yml['tests'].keys():
                        run_tests.append(defined)
                        log.info(" |Queing test => %s " % defined, extra={"nametag": self.nametag})
                        for parms in cfg_yml['tests'][defined].keys():
                            for key in required_test_parameters:
                                if key in cfg_yml['tests'][defined].keys():
                                    pass
                                else:
                                    log.error("No key %s in test" % key + defined)
                                    raise TaskCatException("While inspecting: " + parms)
            else:
                raise TaskCatException("Cannot open [%s]" % yaml_file)
        except TaskCatException:
            raise
        except Exception as e:
            log.debug(str(e))
            raise TaskCatException("config.yml [%s] is not formatted well!!" % yaml_file)
        return run_tests

    def collect_resources(self, testdata_list, logpath):
        """
        This function collects the AWS resources information created by the
        CloudFormation stack for generating the report.

        :param testdata_list: List of TestData object
        :param logpath: Log file path

        """
        resource = {}
        log.info("(Collecting Resources)")
        for test in testdata_list:
            for stack in test.get_test_stacks():
                stackinfo = CommonTools(stack['StackId']).parse_stack_info()
                # Get stack resources
                resource[stackinfo['region']] = (
                    CfnResourceTools(self._boto_client).get_resources(
                        str(stackinfo['stack_name']),
                        str(stackinfo['region'])
                    )
                )
                extension = '.txt'
                test_logpath = '{}/{}-{}-{}{}'.format(
                    logpath,
                    stackinfo['stack_name'],
                    stackinfo['region'],
                    'resources',
                    extension)

                # Write resource logs
                file = open(test_logpath, 'w')
                file.write(str(
                    json.dumps(
                        resource,
                        indent=4,
                        separators=(',', ': '))))
                file.close()

    def createreport(self, testdata_list, filename):
        """
        This function creates the test report.

        :param testdata_list: List of TestData objects
        :param filename: Report file name
        :return:
        """
        o_directory = 'taskcat_outputs'

        # noinspection PyBroadException
        try:
            os.stat(o_directory)
        except TaskCatException:
            raise
        except Exception:
            os.mkdir(o_directory)
        log.info("Creating report in [%s]" % o_directory)
        dashboard_filename = o_directory + "/" + filename

        # Collect recursive logs
        # file path is already setup by getofile function in genreports
        cfn_logs = CfnLogTools(self._boto_client)
        cfn_logs.createcfnlogs(testdata_list, o_directory)

        # Generate html test dashboard
        cfn_report = ReportBuilder(testdata_list, dashboard_filename, self.version, self._boto_client, self)
        cfn_report.generate_report()
