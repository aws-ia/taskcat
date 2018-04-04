#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil tonynv@amazon.com, avattathil@gmail.com
# Shivansh Singh sshvans@amazon.com,
# Santiago Cardenas sancard@amazon.com,
# Jay McConnell jmmccon@amazon.com,
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

import argparse
import base64
import datetime
import json
import os
import random
import re
import sys
import textwrap
import time
import uuid
import boto3
import pyfiglet
import tabulate
import yaml
import yattag
import logging
from argparse import RawTextHelpFormatter
from botocore.vendored import requests
from botocore.exceptions import ClientError
from pkg_resources import get_distribution

from .reaper import Reaper
from .utils import ClientFactory

# Version Tag
'''
:param _run_mode: A value of 1 indicated taskcat is sourced from pip
 A value of 0 indicates development mode taskcat is loading from local source
'''
try:
    __version__ = get_distribution('taskcat').version.replace('.0', '.')
    _run_mode = 1
except Exception:
    __version__ = "[local source] no pip module installed"
    _run_mode = 0

version = __version__
debug = ''
error = ''
check = ''
fail = ''
info = ''
sig = base64.b64decode("dENhVA==").decode()
jobid = str(uuid.uuid4())
header = '\x1b[1;41;0m'
hightlight = '\x1b[0;30;47m'
name_color = '\x1b[0;37;44m'
aqua = '\x1b[0;30;46m'
green = '\x1b[0;30;42m'
white = '\x1b[0;30;47m'
orange = '\x1b[0;30;43m'
red = '\x1b[0;30;41m'
rst_color = '\x1b[0m'
E = '{1}[ERROR {0} ]{2} :'.format(error, red, rst_color)
D = '{1}[DEBUG {0} ]{2} :'.format(debug, aqua, rst_color)
P = '{1}[PASS  {0} ]{2} :'.format(check, green, rst_color)
F = '{1}[FAIL  {0} ]{2} :'.format(fail, red, rst_color)
I = '{1}[INFO  {0} ]{2} :'.format(info, orange, rst_color)

'''
Given the url to PypI package info url returns the current live version
'''

# create logger
logger = logging.getLogger('taskcat')
logger.setLevel(logging.DEBUG)


def get_pip_version(pkginfo_url):
    pkginfo = requests.get(pkginfo_url).text
    for record in pkginfo.split('\n'):
        if record.startswith('Version'):
            current_version = str(record).split(':', 1)
            return (current_version[1]).strip()


def buildmap(start_location, map_string, partial_match=True):
    """
    Given a start location and a string value, this function returns a list of
    file paths containing the given string value, down in the directory
    structure from the start location.

    :param start_location: directory from where to start looking for the file
    :param map_string: value to match in the file path
    :param partial_match: (bool) Turn on partial matching.
    :  Ex: 'foo' matches 'foo' and 'foo.old'. Defaults true. False adds a '/' to the end of the string.
    :return:
        list of file paths containing the given value.
    """
    if not partial_match:
        map_string = "{}/".format(map_string)
    fs_map = []
    for fs_path, dirs, filelist in os.walk(start_location, topdown=False):
        for fs_file in filelist:
            fs_path_to_file = (os.path.join(fs_path, fs_file))
            if map_string in fs_path_to_file and '.git' not in fs_path_to_file:
                fs_map.append(fs_path_to_file)

    return fs_map


"""
    This class is used to represent the test data.
"""


class TestData(object):
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


# noinspection PyUnresolvedReferences
class TaskCat(object):
    # CONSTRUCTOR
    # ============

    def __init__(self, nametag='[taskcat]'):
        self.nametag = '{1}{0}{2}'.format(nametag, name_color, rst_color)
        self.project = None
        self.owner = None
        self.banner = None
        self.capabilities = []
        self.verbose = False
        self.config = 'config.yml'
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
        self._password = None
        self.run_cleanup = True
        self.public_s3_bucket = False
        self._aws_access_key = None
        self._aws_secret_key = None
        self._boto_profile = None
        self._boto_client = ClientFactory(logger=logger)
        self._key_url_map = {}

    # SETTERS AND GETTERS
    # ===================

    def set_project(self, project):
        self.project = project

    def get_project(self):
        return self.project

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
            print("Cannot locate file %s" % config_yml)
            exit(1)

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
        Keys defined in either of these files will override Keys defined in <project>/ci/*.json.

        :param original_keys: json object derived from Parameter Input JSON in <project>/ci/
        """
        # Github/issue/57
        # Look for ~/.taskcat_overrides.json

        # Fetch overrides Homedir first.
        dict_squash_list = []
        _homedir_override_file_path = "{}/.aws/{}".format(os.path.expanduser('~'), 'taskcat_global_override.json')
        if os.path.isfile(_homedir_override_file_path):
            with open(_homedir_override_file_path) as f:
                _homedir_override_json = json.loads(f.read())
                print(D + "Values loaded from ~/.aws/taskcat_global_override.json")
                print(D + str(_homedir_override_json))
            dict_squash_list.append(_homedir_override_json)

        # Now look for per-project override uploaded to S3.
        override_file_key = "{}/ci/taskcat_project_override.json".format(self.project)
        try:
            # Intentional duplication of self.get_content() here, as I don't want to break that due to
            # tweaks necessary here.
            s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)
            dict_object = s3_client.get_object(Bucket=self.s3bucket, Key=override_file_key)
            content = dict_object['Body'].read().strip()
            _obj = json.loads(content)
            dict_squash_list.append(_obj)
            print(D + "Values loaded from {}/ci/taskcat_project_override.json".format(self.project))
            print(D + str(_obj))
        except Exception:
            pass

        # Setup a list index dictionary.
        # - Used to give an Parameter => Index mapping for replacement.
        param_index = {}
        for (idx, param_dict) in enumerate(original_keys):
            key = param_dict['ParameterKey']
            param_index[key] = idx

        # Merge the two lists, overriding the original values if necessary.
        for override in dict_squash_list:
            for override_pd in override:
                key = override_pd['ParameterKey']
                if key in param_index.keys():
                    idx = param_index[key]
                    original_keys[idx] = override_pd
                else:
                    original_keys.append(override_pd)
                    param_index[override_pd['ParameterKey']] = original_keys.index(override_pd)
        # check if s3 bucket and QSS3BucketName param match. fix if they dont.
        bucket_name = self.get_s3bucket()
        _kn = 'QSS3BucketName'
        if _kn in param_index:
            _knidx = param_index[_kn]
            param_bucket_name = original_keys[_knidx]['ParameterValue']
            if (param_bucket_name != bucket_name):
                print(I + "Data inconsistency between S3 Bucket Name [{}] and QSS3BucketName Parameter Value: [{}]".format(bucket_name, param_bucket_name))
                print(I + "Setting the value of QSS3BucketName to [{}]".format(bucket_name))
                original_keys[_knidx]['ParameterValue'] = bucket_name

        return original_keys

    def set_template_path(self, template):
        self.template_path = template

    def get_template_path(self):
        return self.template_path

    def set_password(self, password):
        self._password = password

    def get_password(self):
        return self._password

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
        s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)
        self.set_project(taskcat_cfg['global']['qsname'])

        # TODO Update to alchemist upload
        if 's3bucket' in taskcat_cfg['global'].keys():
            self.set_s3bucket(taskcat_cfg['global']['s3bucket'])
            self.set_s3bucket_type('defined')
            print(I + "Staging Bucket => " + self.get_s3bucket())
        else:
            auto_bucket = 'taskcat-' + self.get_project() + "-" + jobid[:8]
            if self.get_default_region():
                print('{0}Creating bucket {1} in {2}'.format(I, auto_bucket, self.get_default_region()))
                if self.get_default_region() == 'us-east-1':
                    response = s3_client.create_bucket(ACL='public-read',
                                                       Bucket=auto_bucket)
                else:
                    response = s3_client.create_bucket(ACL='public-read',
                                                       Bucket=auto_bucket,
                                                       CreateBucketConfiguration = {
                                                           'LocationConstraint': self.get_default_region()
                                                       }
                                                       )

                self.set_s3bucket_type('auto')
            else:
                print(E + "Default_region = " + self.get_default_region())
                sys.exit(1)

            if response['ResponseMetadata']['HTTPStatusCode'] is 200:
                print(I + "Staging Bucket => [%s]" % auto_bucket)
                self.set_s3bucket(auto_bucket)
            else:
                print('{0}Creating bucket {1} in {2}'.format(I, auto_bucket, self.get_default_region()))
                response = s3_client.create_bucket(ACL='public-read',
                                                   Bucket=auto_bucket,
                                                   CreateBucketConfiguration={
                                                       'LocationConstraint': self.get_default_region()})

                if response['ResponseMetadata']['HTTPStatusCode'] is 200:
                    print(I + "Staging Bucket => [%s]" % auto_bucket)
                    self.set_s3bucket(auto_bucket)

        # TODO Remove after alchemist is implemented

        if os.path.isdir(self.get_project()):
            current_dir = "."
            start_location = "{}/{}".format(".", self.get_project())
            fsmap = buildmap(current_dir, start_location, partial_match=False)
        else:

            print('''\t\t Hint: The name specfied as value of qsname ({})
                    must match the root directory of your project'''.format(self.get_project()))
            print("{0}!Cannot find directory [{1}] in {2}".format(E, self.get_project(), os.getcwd()))
            print(I + "Please cd to where you project is located")
            sys.exit(1)

        for filename in fsmap:
            try:
                upload = re.sub('^./', '', filename)
                s3_client.upload_file(filename, self.get_s3bucket(), upload, ExtraArgs={'ACL': 'public-read'})
            except Exception as e:
                print("Cannot Upload to bucket => %s" % self.get_s3bucket())
                print(E + "Check that you bucketname is correct")
                if self.verbose:
                    print(D + str(e))
                sys.exit(1)

        paginator = s3_client.get_paginator('list_objects')
        operation_parameters = {'Bucket': self.get_s3bucket(), 'Prefix': self.get_project()}
        s3_pages = paginator.paginate(**operation_parameters)

        for s3keys in s3_pages.search('Contents'):
            print("{}[S3: -> ]{} s3://{}/{}".format(white, rst_color, self.get_s3bucket(), s3keys.get('Key')))
        print("{} |Contents of S3 Bucket {} {}".format(self.nametag, header, rst_color))

        print('\n')

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
            print("{0}!Only {1} az's are available in {2}".format(E, len(available_azs), region))
            quit()
        else:
            azs = ','.join(available_azs[:count])
            return azs

    def get_content(self, bucket, object_key):
        """
        Returns the content of an object, given the bucket name and the key of the object

        :param bucket: Bucket name
        :param object_key: Key of the object

        :return: Content of the object

        """
        s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)
        dict_object = s3_client.get_object(Bucket=bucket, Key=object_key)
        content = dict_object['Body'].read().strip()
        return content

    def get_s3contents(self, url):
        """
        Returns S3 object.
        - If --public-s3-bucket is passed, returns via the requests library.
        - If not, does an S3 API call.

        :param url: URL of the S3 object to return.
        :return: Data of the s3 object.
        """
        if self.public_s3_bucket:
            payload = requests.get(url)
            return payload.text
        key = self._key_url_map[url]
        return self.get_content(self.get_s3bucket(), key)

    def get_s3_url(self, key):
        """
        Returns S3 url of a given object.

        :param key: Name of the object whose S3 url is being returned
        :return: S3 url of the given key

        """
        s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)
        bucket_location = s3_client.get_bucket_location(Bucket=self.get_s3bucket())
        _project_s3_prefix = self.get_project()
        paginator = s3_client.get_paginator('list_objects')
        operation_parameters = {'Bucket': self.get_s3bucket(), 'Prefix': _project_s3_prefix}
        page_iterator = paginator.paginate(**operation_parameters)
        for page in page_iterator:
            for s3obj in (page['Contents']):
                for metadata in s3obj.items():
                    if metadata[0] == 'Key':
                        if key in metadata[1]:
                            # Finding exact match
                            terms = metadata[1].split("/")
                            _found_prefix = terms[0]
                            # issues/
                            if (key == terms[-1]) and (_found_prefix == _project_s3_prefix):
                                if bucket_location[
                                    'LocationConstraint'
                                ] is not None:
                                    o_url = "https://s3-{0}.{1}/{2}/{3}".format(
                                        bucket_location['LocationConstraint'],
                                        "amazonaws.com",
                                        self.get_s3bucket(),
                                        metadata[1])
                                    self._key_url_map.update({o_url:metadata[1]})
                                    return o_url
                                else:
                                    amzns3 = 's3.amazonaws.com'
                                    o_url = "https://{1}.{0}/{2}".format(amzns3, self.get_s3bucket(), metadata[1])
                                    self._key_url_map.update({o_url:metadata[1]})
                                    return o_url

    def get_global_region(self, yamlcfg):
        """
        Returns a list of regions defined under global region in the yml config file.

        :param yamlcfg: Content of the yml config file
        :return: List of regions

        """
        g_regions = []
        for keys in yamlcfg['global'].keys():
            if 'region' in keys:
                try:
                    iter(yamlcfg['global']['regions'])
                    namespace = 'global'
                    for region in yamlcfg['global']['regions']:
                        # print("found region %s" % region)
                        g_regions.append(region)
                        self._use_global = True
                except TypeError:
                    print("No regions defined in [%s]:" % namespace)
                    print("Please correct region defs[%s]:" % namespace)
        return g_regions

    def get_resources(self, stackname, region, include_stacks=False):
        """
        Given a stackname, and region function returns the list of dictionary items, where each item
        consist of logicalId, physicalId and resourceType of the aws resource associated
        with the stack.

        :param include_stacks:
        :param stackname: CloudFormation stack name
        :param region: AWS region
        :return: List of objects in the following format
             [
                 {
                     'logicalId': 'string',
                     'physicalId': 'string',
                     'resourceType': 'String'
                 },
             ]

        """
        l_resources = []
        self.get_resources_helper(stackname, region, l_resources, include_stacks)
        return l_resources

    def get_resources_helper(self, stackname, region, l_resources, include_stacks):
        """
        This is a helper function of get_resources function. Check get_resources function for details.

        """
        if stackname != 'None':
            try:
                cfn = self._boto_client.get('cloudformation', region=region)
                result = cfn.describe_stack_resources(StackName=stackname)
                stack_resources = result.get('StackResources')
                for resource in stack_resources:
                    if self.verbose:
                        print(D + "Resources: for {}".format(stackname))
                        print(D + "{0} = {1}, {2} = {3}, {4} = {5}".format(
                            '\n\t\tLogicalId',
                            resource.get('LogicalResourceId'),
                            '\n\t\tPhysicalId',
                            resource.get('PhysicalResourceId'),
                            '\n\t\tType',
                            resource.get('ResourceType')
                        ))
                    # if resource is a stack and has a physical resource id
                    # (NOTE: physical id will be missing if stack creation is failed)
                    if resource.get(
                            'ResourceType') == 'AWS::CloudFormation::Stack' and 'PhysicalResourceId' in resource:
                        if include_stacks:
                            d = {'logicalId': resource.get('LogicalResourceId'),
                                 'physicalId': resource.get('PhysicalResourceId'),
                                 'resourceType': resource.get('ResourceType')}
                            l_resources.append(d)
                        stackdata = self.parse_stack_info(
                            str(resource.get('PhysicalResourceId')))
                        region = stackdata['region']
                        self.get_resources_helper(resource.get('PhysicalResourceId'), region, l_resources,
                                                  include_stacks)
                    # else if resource is not a stack and has a physical resource id
                    # (NOTE: physical id will be missing if stack creation is failed)
                    elif resource.get(
                            'ResourceType') != 'AWS::CloudFormation::Stack' and 'PhysicalResourceId' in resource:
                        d = {'logicalId': resource.get('LogicalResourceId'),
                             'physicalId': resource.get('PhysicalResourceId'),
                             'resourceType': resource.get('ResourceType')}
                        l_resources.append(d)
            except Exception as e:
                if self.verbose:
                    print(D + str(e))
                sys.exit(F + "Unable to get resources for stack %s" % stackname)

    def get_all_resources(self, stackids, region):
        """
        Given a list of stackids, function returns the list of dictionary items, where each
        item consist of stackId and the resources associated with that stack.

        :param stackids: List of Stack Ids
        :param region: AWS region
        :return: A list of dictionary object in the following format
                [
                    {
                        'stackId': 'string',
                        'resources': [
                            {
                               'logicalId': 'string',
                               'physicalId': 'string',
                               'resourceType': 'String'
                            },
                        ]
                    },
                ]

        """
        l_all_resources = []
        for anId in stackids:
            d = {
                'stackId': anId,
                'resources': self.get_resources(anId, region)
            }
            l_all_resources.append(d)
        return l_all_resources

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
            print(self.nametag + " :Validate Template in test[%s]" % test)
            self.define_tests(taskcat_cfg, test)
            try:
                if self.verbose:
                    print(D + "Default region [%s]" % self.get_default_region())
                cfn = self._boto_client.get('cloudformation', region=self.get_default_region())

                cfn.validate_template(TemplateURL=self.get_s3_url(self.get_template_file()))
                result = cfn.validate_template(TemplateURL=self.get_s3_url(self.get_template_file()))
                print(P + "Validated [%s]" % self.get_template_file())
                if 'Description' in result:
                    cfn_result = (result['Description'])
                    print(I + "Description  [%s]" % textwrap.fill(cfn_result))
                else:
                    print(I + "Please include a top-level description for template: [%s]" % self.get_template_file())
                if self.verbose:
                    cfn_params = json.dumps(result['Parameters'], indent=11, separators=(',', ': '))
                    print(D + "Parameters:")
                    print(cfn_params)
            except Exception as e:
                if self.verbose:
                    print(D + str(e))
                sys.exit(F + "Cannot validate %s" % self.get_template_file())
        print('\n')
        return True

    def genpassword(self, pass_length, pass_type):
        """
        Returns a password of given length and type.

        :param pass_length: Length of the desired password
        :param pass_type: Type of the desired password - String only OR Alphanumeric
            * A = AlphaNumeric, Example 'vGceIP8EHC'
        :return: Password of given length and type
        """
        if self.verbose:
            print(D + "Auto generating password")
            print(D + "Pass size => {0}".format(pass_length))

        password = []
        numbers = "1234567890"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        specialchars = "!#$&{*:[=,]-_%@+"

        # Generates password string with:
        # lowercase,uppercase and numeric chars
        if pass_type == 'A':
            print(D + "Pass type => {0}".format('alpha-numeric'))

            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        # Generates password string with:
        # lowercase,uppercase, numbers and special chars
        elif pass_type == 'S':
            print(D + "Pass type => {0}".format('specialchars'))
            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))
                password.append(random.choice(specialchars))
        else:
            # If no passtype is defined (None)
            # Defaults to alpha-numeric
            # Generates password string with:
            # lowercase,uppercase, numbers and special chars
            print(D + "Pass type => default {0}".format('alpha-numeric'))
            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        return ''.join(password)

    def generate_random(self, gtype, length):
        random_string = []
        numbers = "1234567890"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        if gtype == 'alpha':
            print(D + "Random String => {0}".format('alpha'))

            while len(random_string) < length:
                random_string.append(random.choice(lowercase))

        # Generates password string with:
        # lowercase,uppercase, numbers and special chars
        elif gtype == 'number':
            print(D + "Random String => {0}".format('numeric'))
            while len(random_string) < length:
                random_string.append(random.choice(numbers))

        return ''.join(random_string)

    def generate_uuid(self, uuid_type):
        if uuid_type is 'A':
            return str(uuid.uuid4())
        else:
            return str(uuid.uuid4())

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

        # (Generate UUID String)
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

        for parmdict in s_parms:
            for _ in parmdict:

                param_value = parmdict['ParameterValue']

                # Determines the size of the password to generate
                count_re = re.compile('(?!\w+_)\d{1,2}', re.IGNORECASE)

                # Determines the type of password to generate
                gentype_re = re.compile(
                    '(?!\w+_genpass_\d{1,2}])([AS])', re.IGNORECASE)

                # Determines if _genpass has been requested
                genpass_re = re.compile(
                    '\$\[\w+_genpass?(\w)_\d{1,2}\w?]$', re.IGNORECASE)

                # Determines if random string  value was requested
                gen_string_re = re.compile(
                    '\$\[taskcat_random-string]$', re.IGNORECASE)

                # Determines if random number value was requested
                gen_numbers_re = re.compile(
                    '\$\[taskcat_random-numbers]$', re.IGNORECASE)

                # Determines if autobucket value was requested
                autobucket_re = re.compile(
                    '\$\[taskcat_autobucket]$', re.IGNORECASE)

                # Determines if _genaz has been requested. This can return single or multiple AZs.
                genaz_re = re.compile('\$\[\w+_ge[nt]az_\d]', re.IGNORECASE)

                # Determines if single AZ has been requested. This is added to support legacy templates
                genaz_single_re = re.compile('\$\[\w+_ge[nt]singleaz_\d]', re.IGNORECASE)

                # Determines if uuid has been requested
                genuuid_re = re.compile('\$\[\w+_gen[gu]uid]', re.IGNORECASE)

                # Determines if AWS QuickStart default KeyPair name has been requested
                getkeypair_re = re.compile('\$\[\w+_getkeypair]', re.IGNORECASE)

                # Determines if AWS QuickStart default license bucket name has been requested
                getlicensebucket_re = re.compile('\$\[\w+_getlicensebucket]', re.IGNORECASE)

                # Determines if AWS QuickStart default media bucket name has been requested
                getmediabucket_re = re.compile('\$\[\w+_getmediabucket]', re.IGNORECASE)

                # Determines if license content has been requested
                licensecontent_re = re.compile('\$\[\w+_getlicensecontent]', re.IGNORECASE)

                # Determines if s3 replacement was requested
                gets3replace = re.compile('\$\[\w+_url_.+]$', re.IGNORECASE)
                geturl_re = re.compile('(?<=._url_)(.+)(?=]$)', re.IGNORECASE)

                if gen_string_re.search(param_value):
                    random_string = self.regxfind(gen_string_re, param_value)
                    param_value = self.generate_random('alpha', 20)

                    if self.verbose:
                        print("{}Generating random string for {}".format(D, random_string))
                    parmdict['ParameterValue'] = param_value

                if gen_numbers_re.search(param_value):
                    random_numbers = self.regxfind(gen_numbers_re, param_value)
                    param_value = self.generate_random('number', 20)

                    if self.verbose:
                        print("{}Generating numeric string for {}".format(D, random_numbers))
                    parmdict['ParameterValue'] = param_value

                if genuuid_re.search(param_value):
                    uuid_string = self.regxfind(genuuid_re, param_value)
                    param_value = self.generate_uuid('A')

                    if self.verbose:
                        print("{}Generating random uuid string for {}".format(D, uuid_string))
                    parmdict['ParameterValue'] = param_value

                if autobucket_re.search(param_value):
                    bkt = self.regxfind(autobucket_re, param_value)
                    param_value = self.get_s3bucket()
                    if self.verbose:
                        print("{}Setting value to {}".format(D, bkt))
                    parmdict['ParameterValue'] = param_value

                if gets3replace.search(param_value):
                    url = self.regxfind(geturl_re, param_value)
                    param_value = self.get_s3contents(url)
                    if self.verbose:
                        print("{}Raw content of url {}".format(D, url))
                    parmdict['ParameterValue'] = param_value

                if getkeypair_re.search(param_value):
                    keypair = self.regxfind(getkeypair_re, param_value)
                    param_value = 'cikey'
                    if self.verbose:
                        print("{}Generating default Keypair {}".format(D, keypair))
                    parmdict['ParameterValue'] = param_value

                if getlicensebucket_re.search(param_value):
                    licensebucket = self.regxfind(getlicensebucket_re, param_value)
                    param_value = 'quickstart-ci-license'
                    if self.verbose:
                        print("{}Generating default license bucket {}".format(D, licensebucket))
                    parmdict['ParameterValue'] = param_value

                if getmediabucket_re.search(param_value):
                    media_bucket = self.regxfind(getmediabucket_re, param_value)
                    param_value = 'quickstart-ci-media'
                    if self.verbose:
                        print("{}Generating default media bucket {}".format(D, media_bucket))
                    parmdict['ParameterValue'] = param_value

                if licensecontent_re.search(param_value):
                    license_bucket = 'quickstart-ci-license'
                    licensekey = (self.regxfind(licensecontent_re, param_value)).strip('/')
                    param_value = self.get_content(license_bucket, licensekey)
                    if self.verbose:
                        print("{}Getting license content for {}/{}".format(D, license_bucket, licensekey))
                    parmdict['ParameterValue'] = param_value

                # Autogenerated value to password input in runtime
                if genpass_re.search(param_value):
                    passlen = int(
                        self.regxfind(count_re, param_value))
                    gentype = self.regxfind(
                        gentype_re, param_value)
                    if not gentype:
                        # Set default password type
                        # A value of D will generate a simple alpha
                        # aplha numeric password
                        gentype = 'D'

                    if passlen:
                        if self.verbose:
                            print("{}AutoGen values for {}".format(D, param_value))
                        param_value = self.genpassword(
                            passlen, gentype)
                        parmdict['ParameterValue'] = param_value

                if genaz_re.search(param_value):
                    numazs = int(
                        self.regxfind(count_re, param_value))
                    if numazs:
                        if self.verbose:
                            print(D + "Selecting availability zones")
                            print(D + "Requested %s az's" % numazs)

                        param_value = self.get_available_azs(
                            region,
                            numazs)
                        parmdict['ParameterValue'] = param_value
                    else:
                        print(I + "$[taskcat_genaz_(!)]")
                        print(I + "Number of az's not specified!")
                        print(I + " - (Defaulting to 1 az)")
                        param_value = self.get_available_azs(
                            region,
                            1)
                        parmdict['ParameterValue'] = param_value

                if genaz_single_re.search(param_value):
                    print(D + "Selecting availability zones")
                    print(D + "Requested 1 az")
                    param_value = self.get_available_azs(
                        region,
                        1)
                    parmdict['ParameterValue'] = param_value
        return s_parms

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
        self.set_capabilities('CAPABILITY_NAMED_IAM')
        for test in test_list:
            testdata = TestData()
            testdata.set_test_name(test)
            print("{0}{1}|PREPARING TO LAUNCH => {2}{3}".format(I, header, test, rst_color))
            sname = str(sig)

            stackname = sname + '-' + sprefix + '-' + test + '-' + jobid[:8]
            self.define_tests(taskcat_cfg, test)
            for region in self.get_test_region():
                print(I + "Preparing to launch in region [%s] " % region)
                try:
                    cfn = self._boto_client.get('cloudformation', region=region)
                    s_parmsdata = self.get_s3contents(self.get_parameter_path())
                    s_parms = json.loads(s_parmsdata)
                    s_include_params = self.get_param_includes(s_parms)
                    if s_include_params:
                        s_parms = s_include_params
                    j_params = self.generate_input_param_values(s_parms, region)
                    if self.verbose:
                        print(D + "Creating Boto Connection region=%s" % region)
                        print(D + "StackName=" + stackname)
                        print(D + "DisableRollback=True")
                        print(D + "TemplateURL=%s" % self.get_template_path())
                        print(D + "Capabilities=%s" % self.get_capabilities())
                        print(D + "Parameters:")
                        if self.get_template_type() == 'json':
                            print(json.dumps(j_params, sort_keys=True, indent=11, separators=(',', ': ')))

                    stackdata = cfn.create_stack(
                        StackName=stackname,
                        DisableRollback=True,
                        TemplateURL=self.get_template_path(),
                        Parameters=j_params,
                        Capabilities=self.get_capabilities())

                    testdata.add_test_stack(stackdata)

                except Exception as e:
                    if self.verbose:
                        print(E + str(e))
                    sys.exit(F + "Cannot launch %s" % self.get_template_file())

            testdata_list.append(testdata)
        print('\n')
        for test in testdata_list:
            for stack in test.get_test_stacks():
                print("{} |{}LAUNCHING STACKS{}".format(self.nametag, header, rst_color))
                print("{} {}{} {} {}".format(
                    I,
                    header,
                    test.get_test_name(),
                    str(stack['StackId']).split(':stack', 1),
                    rst_color))
        return testdata_list

    def validate_parameters(self, taskcat_cfg, test_list):
        """
        This function validates the parameters file of the CloudFormation template.

        :param taskcat_cfg: TaskCat config yaml object
        :param test_list: List of tests

        :return: TRUE if the parameters file is valid, else FALSE
        """
        for test in test_list:
            self.define_tests(taskcat_cfg, test)
            print(self.nametag + " |Validate JSON input in test[%s]" % test)
            if self.verbose:
                print(D + "parameter_path = %s" % self.get_parameter_path())

            inputparms = self.get_s3contents(self.get_parameter_path())
            jsonstatus = self.check_json(inputparms)

            if self.verbose:
                print(D + "jsonstatus = %s" % jsonstatus)

            if jsonstatus:
                print(P + "Validated [%s]" % self.get_parameter_file())
            else:
                print(D + "parameter_file = %s" % self.get_parameter_file())
                sys.exit(F + "Cannot validate %s" % self.get_parameter_file())
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

    def parse_stack_info(self, stack_name):
        """
        Returns a dictionary object containing the region and stack name.

        :param stack_name: Full stack name arn
        :return: Dictionary object containing the region and stack name

        """
        stack_info = dict()

        region_re = re.compile('(?<=:)(.\w-.+(\w*)-\d)(?=:)')
        stack_name_re = re.compile('(?<=:stack/)(tCaT.*.)(?=/)')
        stack_info['region'] = self.regxfind(region_re, stack_name)
        stack_info['stack_name'] = self.regxfind(stack_name_re, stack_name)
        return stack_info

    def stackcheck(self, stack_id):
        """
        Given the stack id, this function returns the status of the stack as
        a list with stack name, region, and status as list items, in the respective
        order.

        :param stack_id: CloudFormation stack id

        :return: List containing the stack name, region and stack status in the
            respective order.
        """
        stackdata = self.parse_stack_info(stack_id)
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
            print('Creating new [{}]'.format(table_name))
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            return table

        except Exception as notable:
            if notable:
                print('Adding to existing [{}]'.format(table_name))
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
                'test-outputs': jobid[:8],
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
        print('\n')
        while active_tests > 0:
            current_active_tests = 0
            print(I + "{}{} {} [{}]{}".format(
                header,
                'AWS REGION'.ljust(15),
                'CLOUDFORMATION STACK STATUS'.ljust(25),
                'CLOUDFORMATION STACK NAME',
                rst_color))

            time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for test in testdata_list:
                for stack in test.get_test_stacks():
                    stackquery = self.stackcheck(str(stack['StackId']))
                    current_active_tests = stackquery[
                                               3] + current_active_tests
                    logs = (I + "{3}{0} {1} [{2}]{4}".format(
                        stackquery[1].ljust(15),
                        stackquery[2].ljust(25),
                        stackquery[0],
                        hightlight,
                        rst_color))
                    print(logs)
                    if self._enable_dynamodb:
                        table = self.db_initproject(self.get_project())
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
            print('\n')

    def cleanup(self, testdata_list, speed):
        """
        This function deletes the CloudFormation stacks of the given tests.

        :param testdata_list: List of TestData objects
        :param speed: Interval (in seconds) in which the status has to be checked
            while deleting the stacks.

        """

        docleanup = self.get_docleanup()
        if self.verbose:
            print(D + "clean-up = %s " % str(docleanup))

        if docleanup:
            print("{} |CLEANUP STACKS{}".format(self.nametag, header, rst_color))
            self.stackdelete(testdata_list)
            self.get_stackstatus(testdata_list, speed)
            self.deep_cleanup(testdata_list)
        else:
            print(I + "[Retaining Stacks (Cleanup is set to {0}]".format(docleanup))

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
                print(I + "All stacks deleted successfully. Deep clean-up not required.")
                continue

            print(I + "Few stacks failed to delete. Collecting resources for deep clean-up.")
            # get test region from the stack id
            stackdata = self.parse_stack_info(
                str(failed_stack_ids[0]))
            region = stackdata['region']
            session = boto3.session.Session(region_name=region)
            s = Reaper(session)
            failed_stacks = self.get_all_resources(failed_stack_ids, region)
            # print all resources which failed to delete
            if self.verbose:
                print(D + "Resources which failed to delete:\n")
                for failed_stack in failed_stacks:
                    print(D + "Stack Id: " + failed_stack['stackId'])
                    for res in failed_stack['resources']:
                        print(D + "{0} = {1}, {2} = {3}, {4} = {5}".format(
                            '\n\t\tLogicalId',
                            res.get('logicalId'),
                            '\n\t\tPhysicalId',
                            res.get('physicalId'),
                            '\n\t\tType',
                            res.get('resourceType')
                        ))
                s.delete_all(failed_stacks)

        # Check to see if auto bucket was created
        if self.get_s3bucket_type() is 'auto':
            print(I + "(Cleaning up staging assets)")

            s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)

            # Batch object processing by pages
            paginator = s3_client.get_paginator('list_objects')
            operation_parameters = {'Bucket': self.get_s3bucket(), 'Prefix': self.get_project()}
            s3_pages = paginator.paginate(**operation_parameters)

            # Load objects to delete
            objects_in_s3 = 1
            delete_keys = dict(Objects=[])
            for key in s3_pages.search('Contents'):
                delete_keys['Objects'].append(dict(Key=key['Key']))
                objects_in_s3 += 1
                if objects_in_s3 == 1000:
                    # Batch delete 1000 objects at a time
                    s3_client.delete_objects(Bucket=self.get_s3bucket(), Delete=delete_keys)
                    print(I + "Deleted {} objects from {}".format(objects_in_s3, self.get_s3bucket()))

                    delete_keys = dict(Objects=[])
                    objects_in_s3 = 1

            # Delete last batch of objects
            if objects_in_s3 > 1:
                s3_client.delete_objects(Bucket=self.get_s3bucket(), Delete=delete_keys)
                print(I + "Deleted {} objects from {}".format(objects_in_s3, self.get_s3bucket()))

            # Delete bucket
            s3_client.delete_bucket(
                Bucket=self.get_s3bucket())
            if self.verbose:
                print(D + "Deleting Bucket {0}".format(self.get_s3bucket()))

        else:
            print(I + "Retaining assets in s3bucket [{0}]".format(self.get_s3bucket()))

    def stackdelete(self, testdata_list):
        """
        This function deletes the CloudFormation stacks of the given tests.

        :param testdata_list: List of TestData objects

        """
        for test in testdata_list:
            for stack in test.get_test_stacks():
                stackdata = self.parse_stack_info(
                    str(stack['StackId']))
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
            # print("[DEBUG] tdefs = %s" % tdefs)
            if tdefs == test:
                t = yamlc['tests'][test]['template_file']
                p = yamlc['tests'][test]['parameter_input']
                n = yamlc['global']['qsname']
                o = yamlc['global']['owner']
                b = self.get_s3bucket()

                # Checks if cleanup flag is set
                # If cleanup is set to 'false' stack will not be deleted after
                # launch attempt
                if 'cleanup' in yamlc['global'].keys():
                    cleanupstack = yamlc['global']['cleanup']
                    if cleanupstack:
                        if self.verbose:
                            print(D + "cleanup set to ymal value")
                            self.set_docleanup(cleanupstack)
                    else:
                        print(I + "Cleanup value set to (false)")
                        self.set_docleanup(False)
                else:
                    # By default do cleanup unless self.run_cleanup
                    # was overridden (set to False) by -n flag
                    if not self.run_cleanup:
                        if self.verbose:
                            print(D + "cleanup set by cli flag {0}".format(self.run_cleanup))
                    else:
                        self.set_docleanup(True)
                        if self.verbose:
                            print(I + "No cleanup value set")
                            print(I + " - (Defaulting to cleanup)")

                # Load test setting
                self.set_s3bucket(b)
                self.set_project(n)
                self.set_owner(o)
                self.set_template_file(t)
                self.set_parameter_file(p)
                self.set_template_path(
                    self.get_s3_url(self.get_template_file()))
                self.set_parameter_path(
                    self.get_s3_url(self.get_parameter_file()))

                # Check to make sure template filenames are correct
                template_path = self.get_template_path()
                if not template_path:
                    print("{0} Could not locate {1}".format(E, self.get_template_file()))
                    print("{0} Check to make sure filename is correct?".format(E, self.get_template_path()))
                    quit()

                # Check to make sure parameter filenames are correct
                parameter_path = self.get_parameter_path()
                if not parameter_path:
                    print("{0} Could not locate {1}".format(E, self.get_parameter_file()))
                    print("{0} Check to make sure filename is correct?".format(E, self.get_parameter_file()))
                    quit()

                # Detect template type

                cfntemplate = self.get_s3contents(self.get_s3_url(self.get_template_file()))

                if self.check_json(cfntemplate, quite=True, strict=False):
                    self.set_template_type('json')
                    # Enforce strict json syntax
                    if self._strict_syntax_json:
                        self.check_json(cfntemplate, quite=True, strict=True)
                else:
                    self.set_template_type(None)
                    self.check_yaml(cfntemplate, quite=True, strict=False)
                    self.set_template_type('yaml')

                if self.verbose:
                    print(I + "|Acquiring tests assets for .......[%s]" % test)
                    print(D + "|S3 Bucket     => [%s]" % self.get_s3bucket())
                    print(D + "|Project       => [%s]" % self.get_project())
                    print(D + "|Template      => [%s]" % self.get_template_path())
                    print(D + "|Parameter     => [%s]" % self.get_parameter_path())
                    print(D + "|TemplateType  => [%s]" % self.get_template_type())

                if 'regions' in yamlc['tests'][test]:
                    if yamlc['tests'][test]['regions'] is not None:
                        r = yamlc['tests'][test]['regions']
                        self.set_test_region(list(r))
                        if self.verbose:
                            print(D + "|Defined Regions:")
                            for list_o in self.get_test_region():
                                print("\t\t\t - [%s]" % list_o)
                else:
                    global_regions = self.get_global_region(yamlc)
                    self.set_test_region(list(global_regions))
                    if self.verbose:
                        print(D + "|Global Regions:")
                        for list_o in self.get_test_region():
                            print("\t\t\t - [%s]" % list_o)
                print(P + "(Completed) acquisition of [%s]" % test)
                print('\n')

    def check_json(self, jsonin, quite=None, strict=None):
        """
        This function validates the given JSON.

        :param jsonin: Json object to be validated
        :param quite: Optional value, if set True suppress verbose output
        :param strict: Optional value, Display errors and exit

        :return: TRUE if given Json is valid, FALSE otherwise.
        """
        try:
            parms = json.loads(jsonin)
            if self.verbose:
                if not quite:
                    print(json.dumps(parms, sort_keys=True, indent=11, separators=(',', ': ')))
        except ValueError as e:
            if strict:
                print(E + str(e))
                sys.exit(1)
            return False
        return True

    def check_yaml(self, yamlin, quite=None, strict=None):
        """
        This function validates the given YAML.

        :param yamlin: Yaml object to be validated
        :param quite: Optional value, if set True suppress verbose output
        :param strict: Optional value, Display errors and exit

        :return: TRUE if given yaml is valid, FALSE otherwise.
        """
        try:
            parms = yaml.load(yamlin)
            if self.verbose:
                if not quite:
                    print(yaml.dump(parms))
        except yaml.YAMLError as e:
            if strict:
                print(E + str(e))
                sys.exit(1)
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
        print('\n')
        if args.boto_profile:
            self._auth_mode = 'profile'
            self._boto_profile = args.boto_profile
            try:
                sts_client = self._boto_client.get('sts',
                                                   profile_name=self._boto_profile,
                                                   region=self.get_default_region())
                account = sts_client.get_caller_identity().get('Account')
                print(self.nametag + " :AWS AccountNumber: \t [%s]" % account)
                print(self.nametag + " :Authenticated via: \t [%s]" % self._auth_mode)
            except Exception as e:
                print(E + "Credential Error - Please check you profile!")
                if self.verbose:
                    print(D + str(e))
                sys.exit(1)
        elif args.aws_access_key and args.aws_secret_key:
            self._auth_mode = 'keys'
            self._aws_access_key = args.aws_access_key
            self._aws_secret_key = args.aws_secret_key

            try:

                sts_client = self._boto_client.get('sts',
                                                   aws_access_key_id=self._aws_access_key,
                                                   aws_secret_access_key=self._aws_secret_key,
                                                   region=self.get_default_region())
                account = sts_client.get_caller_identity().get('Account')
                print(self.nametag + " :AWS AccountNumber: \t [%s]" % account)
                print(self.nametag + " :Authenticated via: \t [%s]" % self._auth_mode)
            except Exception as e:
                print(E + "Credential Error - Please check you keys!")
                if self.verbose:
                    print(D + str(e))
        else:
            self._auth_mode = 'environment'
            if os.environ.get('AWS_DEFAULT_REGION'):
                self.set_default_region(os.environ.get('AWS_DEFAULT_REGION'))
                print(I + "Using environmental region set in $AWS_DEFAULT_REGION")
            else:
                self.set_default_region('us-east-1')

            try:
                sts_client = self._boto_client.get('sts',
                                                   region=self.get_default_region())
                account = sts_client.get_caller_identity().get('Account')
                print(self.nametag + " :AWS AccountNumber: \t [%s]" % account)
                print(self.nametag + " :Authenticated via: \t [%s]" % self._auth_mode)
            except Exception as e:
                print(E + "Credential Error - Please check your boto environment variable !")
                if self.verbose:
                    print(D + str(e))
                sys.exit(1)

    def validate_yaml(self, yaml_file):
        """
        This function validates the given yaml file.

        :param yaml_file: Yaml file name

        """
        print('\n')
        run_tests = []
        required_global_keys = [
            'qsname',
            'owner',
            'reporting',
            'regions'
        ]

        required_test_parameters = [
            'template_file',
            'parameter_input'
        ]
        try:
            if os.path.isfile(yaml_file):
                print(self.nametag + " :Reading Config form: {0}".format(yaml_file))
                with open(yaml_file, 'r') as checkyaml:
                    cfg_yml = yaml.load(checkyaml.read())
                    for key in required_global_keys:
                        if key in cfg_yml['global'].keys():
                            pass
                        else:
                            print("global:%s missing from " % key + yaml_file)
                            sys.exit(1)

                    for defined in cfg_yml['tests'].keys():
                        run_tests.append(defined)
                        print(self.nametag + " |Queing test => %s " % defined)
                        for parms in cfg_yml['tests'][defined].keys():
                            for key in required_test_parameters:
                                if key in cfg_yml['tests'][defined].keys():
                                    pass
                                else:
                                    print("No key %s in test" % key + defined)
                                    print(E + "While inspecting: " + parms)
                                    sys.exit(1)
            else:
                print(E + "Cannot open [%s]" % yaml_file)
                sys.exit(1)
        except Exception as e:
            print(E + "config.yml [%s] is not formatted well!!" % yaml_file)
            if self.verbose:
                print(D + str(e))
            sys.exit(1)
        return run_tests

    def genreport(self, testdata_list, dashboard_filename):
        """
        This function generates the test report.

        :param testdata_list: List of TestData objects
        :param dashboard_filename: Report file name

        """
        doc = yattag.Doc()

        # Type of cfnlog return cfn log file
        # Type of resource_log return resource log file
        def getofile(region, stack_name, resource_type):
            extension = '.txt'
            if resource_type == 'cfnlog':
                location = "{}-{}-{}{}".format(stack_name, region, 'cfnlogs', extension)
                return str(location)
            elif resource_type == 'resource_log':
                location = "{}-{}-{}{}".format(stack_name, region, 'resources', extension)
                return str(location)

        def get_teststate(stackname, region):
            rstatus = None
            status_css = None
            try:
                cfn = self._boto_client.get('cloudformation', region)
                test_query = cfn.describe_stacks(StackName=stackname)

                for result in test_query['Stacks']:
                    rstatus = result.get('StackStatus')
                    if rstatus == 'CREATE_COMPLETE':
                        status_css = 'class=test-green'
                    elif rstatus == 'CREATE_FAILED':
                        status_css = 'class=test-red'
                    else:
                        status_css = 'class=test-red'
            except Exception as e:
                print(E + "Error describing stack named [%s] " % stackname)
                if self.verbose:
                    print(D + str(e))
                rstatus = 'MANUALLY_DELETED'
                status_css = 'class=test-orange'

            return rstatus, status_css

        tag = doc.tag
        text = doc.text
        logo = 'taskcat'
        repo_link = 'https://github.com/aws-quickstart/taskcat'
        css_url = 'https://raw.githubusercontent.com/aws-quickstart/taskcat/master/assets/css/taskcat_reporting.css'
        output_css = requests.get(css_url).text
        doc_link = 'http://taskcat.io'

        with tag('html'):
            with tag('head'):
                doc.stag('meta', charset='utf-8')
                doc.stag(
                    'meta', name="viewport", content="width=device-width")
                with tag('style', type='text/css'):
                    text(output_css)
                with tag('title'):
                    text('TaskCat Report')

            with tag('body'):
                tested_on = time.strftime('%A - %b,%d,%Y @ %H:%M:%S')

                with tag('table', 'class=header-table-fill'):
                    with tag('tbody'):
                        with tag('th', 'colspan=2'):
                            with tag('tr'):
                                with tag('td'):
                                    with tag('a', href=repo_link):
                                        text('GitHub Repo: ')
                                        text(repo_link)
                                        doc.stag('br')
                                    with tag('a', href=doc_link):
                                        text('Documentation: ')
                                        text(doc_link)
                                        doc.stag('br')
                                    text('Tested on: ')
                                    text(tested_on)
                                with tag('td', 'class=taskcat-logo'):
                                    with tag('h3'):
                                        text(logo)
            doc.stag('p')
            with tag('table', 'class=table-fill'):
                with tag('tbody'):
                    with tag('thread'):
                        with tag('tr'):
                            with tag('th',
                                     'class=text-center',
                                     'width=25%'):
                                text('Test Name')
                            with tag('th',
                                     'class=text-left',
                                     'width=10%'):
                                text('Tested Region')
                            with tag('th',
                                     'class=text-left',
                                     'width=30%'):
                                text('Stack Name')
                            with tag('th',
                                     'class=text-left',
                                     'width=20%'):
                                text('Tested Results')
                            with tag('th',
                                     'class=text-left',
                                     'width=15%'):
                                text('Test Logs')

                            for test in testdata_list:
                                with tag('tr', 'class= test-footer'):
                                    with tag('td', 'colspan=5'):
                                        text('')

                                testname = test.get_test_name()
                                print(I + "(Generating Reports)")
                                print(I + " - Processing {}".format(testname))
                                for stack in test.get_test_stacks():
                                    state = self.parse_stack_info(
                                        str(stack['StackId']))
                                    status, css = get_teststate(
                                        state['stack_name'],
                                        state['region'])

                                    with tag('tr'):
                                        with tag('td',
                                                 'class=test-info'):
                                            with tag('h3'):
                                                text(testname)
                                        with tag('td',
                                                 'class=text-left'):
                                            text(state['region'])
                                        with tag('td',
                                                 'class=text-left'):
                                            text(state['stack_name'])
                                        with tag('td', css):
                                            text(str(status))
                                        with tag('td',
                                                 'class=text-left'):
                                            clog = getofile(
                                                state['region'],
                                                state['stack_name'],
                                                'cfnlog')
                                            # rlog = getofile(
                                            #    state['region'],
                                            #    state['stack_name'],
                                            #    'resource_log')
                                            #
                                            with tag('a', href=clog):
                                                text('View Logs ')
                                                # with tag('a', href=rlog):
                                                #    text('Resource Logs ')
                            with tag('tr', 'class= test-footer'):
                                with tag('td', 'colspan=5'):
                                    vtag = 'Generated by {} {}'.format('taskcat', version)
                                    text(vtag)

                        doc.stag('p')
                        print('\n')

        htmloutput = yattag.indent(doc.getvalue(),
                                   indentation='    ',
                                   newline='\r\n',
                                   indent_text=True)

        file = open(dashboard_filename, 'w')
        file.write(htmloutput)
        file.close()

        return htmloutput

    def collect_resources(self, testdata_list, logpath):
        """
        This function collects the AWS resources information created by the
        CloudFormation stack for generating the report.

        :param testdata_list: List of TestData object
        :param logpath: Log file path

        """
        resource = {}
        print(I + "(Collecting Resources)")
        for test in testdata_list:
            for stack in test.get_test_stacks():
                stackinfo = self.parse_stack_info(str(stack['StackId']))
                # Get stack resources
                resource[stackinfo['region']] = (
                    self.get_resources(
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

    def get_cfnlogs(self, stackname, region):
        """
        This function returns the event logs of the given stack in a specific format.
        :param stackname: Name of the stack
        :param region: Region stack belongs to
        :return: Event logs of the stack
        """

        print(I + "Collecting logs for " + stackname + "\"\n")
        # Collect stack_events
        stack_events = get_cfn_stack_events(self, stackname, region)
        # Uncomment line for debug
        # pprint.pprint (stack_events)
        events = []
        for event in stack_events:
            event_details = {'TimeStamp': event['Timestamp'],
                             'ResourceStatus': event['ResourceStatus'],
                             'ResourceType': event['ResourceType'],
                             'LogicalResourceId': event['LogicalResourceId']}
            if 'ResourceStatusReason' in event:
                event_details['ResourceStatusReason'] = event['ResourceStatusReason']
            else:
                event_details['ResourceStatusReason'] = ''

            events.append(event_details)

        return events

    def createcfnlogs(self, testdata_list, logpath):
        """
        This function creates the CloudFormation log files.

        :param testdata_list: List of TestData objects
        :param logpath: Log file path
        :return:
        """
        print("{}Collecting CloudFormation Logs".format(I))
        for test in testdata_list:
            for stack in test.get_test_stacks():
                stackinfo = self.parse_stack_info(str(stack['StackId']))
                stackname = str(stackinfo['stack_name'])
                region = str(stackinfo['region'])
                extension = '.txt'
                test_logpath = '{}/{}-{}-{}{}'.format(
                    logpath,
                    stackname,
                    region,
                    'cfnlogs',
                    extension)
                self.write_logs(str(stack['StackId']), test_logpath)

    def write_logs(self, stack_id, logpath):
        """
        This function writes the event logs of the given stack and all the child stacks to a given file.
        :param stack_id: Stack Id
        :param logpath: Log file path
        :return:
        """
        stackinfo = self.parse_stack_info(str(stack_id))
        stackname = str(stackinfo['stack_name'])
        region = str(stackinfo['region'])

        # Get stack resources
        cfnlogs = self.get_cfnlogs(stackname, region)

        if len(cfnlogs) != 0:
            if cfnlogs[0]['ResourceStatus'] != 'CREATE_COMPLETE':
                if 'ResourceStatusReason' in cfnlogs[0]:
                    reason = cfnlogs[0]['ResourceStatusReason']
                else:
                    reason = 'Unknown'
            else:
                reason = "Stack launch was successful"

            print("\t |StackName: " + stackname)
            print("\t |Region: " + region)
            print("\t |Logging to: " + logpath)
            print("\t |Tested on: " + str(datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")))
            print("------------------------------------------------------------------------------------------")
            print("ResourceStatusReason: ")
            print(textwrap.fill(str(reason), 85))
            print("==========================================================================================")
            with open(logpath, "a") as log_output:
                log_output.write("-----------------------------------------------------------------------------\n")
                log_output.write("Region: " + region + "\n")
                log_output.write("StackName: " + stackname + "\n")
                log_output.write("*****************************************************************************\n")
                log_output.write("ResourceStatusReason:  \n")
                log_output.write(textwrap.fill(str(reason), 85) + "\n")
                log_output.write("*****************************************************************************\n")
                log_output.write("*****************************************************************************\n")
                log_output.write("Events:  \n")
                log_output.writelines(tabulate.tabulate(cfnlogs, headers="keys"))
                log_output.write(
                    "\n*****************************************************************************\n")
                log_output.write("-----------------------------------------------------------------------------\n")
                log_output.write("Tested on: " + datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p") + "\n")
                log_output.write(
                    "-----------------------------------------------------------------------------\n\n")
                log_output.close()

            # Collect resources of the stack and get event logs for any child stacks
            resources = self.get_resources(stackname, region, include_stacks=True)
            for resource in resources:
                if resource['resourceType'] == 'AWS::CloudFormation::Stack':
                    self.write_logs(resource['physicalId'], logpath)
        else:
            print(E + "No event logs found. Something went wrong at describe event call.\n")

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
        except Exception:
            os.mkdir(o_directory)
        print("{} |GENERATING REPORTS{}".format(self.nametag, header, rst_color))
        print(I + "Creating report in [%s]" % o_directory)
        dashboard_filename = o_directory + "/" + filename

        # Collect recursive logs
        # file path is already setup by getofile function in genreports
        self.createcfnlogs(testdata_list, o_directory)

        # Generate html test dashboard
        # Uses logpath + region to create View Logs link
        self.genreport(testdata_list, dashboard_filename)

    @property
    def interface(self):
        parser = argparse.ArgumentParser(
            description="""
            Multi-Region CloudFormation Test Deployment Tool)
            For more info see: http://taskcat.io
        """,
            prog='taskcat',
            prefix_chars='-',
            formatter_class=RawTextHelpFormatter)
        parser.add_argument(
            '-c',
            '--config_yml',
            type=str,
            help=" (Config File Required!) \n "
                 "example here: https://raw.githubusercontent.com/aws-quickstart/"
                 "taskcat/master/examples/sample-taskcat-project/ci/taskcat.yml"
        )
        parser.add_argument(
            '-P',
            '--boto_profile',
            type=str,
            help="Authenticate using boto profile")
        parser.add_argument(
            '-A',
            '--aws_access_key',
            type=str,
            help="AWS Access Key")
        parser.add_argument(
            '-S',
            '--aws_secret_key',
            type=str,
            help="AWS Secret Key")
        parser.add_argument(
            '-n',
            '--no_cleanup',
            action='store_true',
            help="Sets cleanup to false (Does not teardown stacks)")
        parser.add_argument(
            '-v',
            '--verbose',
            action='store_true',
            help="Enables verbosity")
        parser.add_argument(
            '--public_s3_bucket',
            action='store_true',
            help="Sets public_s3_bucket to True. (Accesses objects via public HTTP, not S3 API calls)")
        args = parser.parse_args()

        if len(sys.argv) == 1:
            print(parser.print_help())
            sys.exit(0)

        if args.verbose:
            self.verbose = True
        # Overrides Defaults for cleanup but does not overwrite config.yml
        if args.no_cleanup:
            self.run_cleanup = False

        if args.boto_profile is not None:
            if args.aws_access_key is not None or args.aws_secret_key is not None:
                parser.error("Cannot use boto profile -P (--boto_profile)" +
                             "with --aws_access_key or --aws_secret_key")
                print(parser.print_help())
                sys.exit(1)
        if args.public_s3_bucket:
            self.public_s3_bucket = True

        return args

    @staticmethod
    def checkforupdate():

        def _print_upgrade_msg(newversion):
            print("version %s" % version)
            print('\n')
            print("{} A newer version of {} is available ({})".format(
                I, 'taskcat', newversion))
            print('{} To upgrade pip version    {}[ pip install --upgrade taskcat]{}'.format(
                I, hightlight, rst_color))
            print('{} To upgrade docker version {}[ docker pull taskcat/taskcat ]{}'.format(
                I, hightlight, rst_color))
            print('\n')

        if _run_mode > 0:
            if 'dev' not in version:
                current_version = get_pip_version(
                    'https://pypi.python.org/pypi?name=taskcat&:action=display_pkginfo')
                if version in current_version:
                    print("version %s" % version)
                else:
                    _print_upgrade_msg(current_version)

            else:
                current_version = get_pip_version(
                    'https://testpypi.python.org/pypi?name=taskcat&:action=display_pkginfo')
                if version in current_version:
                    print("version %s" % version)
                else:
                    _print_upgrade_msg(current_version)
        else:
            print(I + "using %s (development mode) \n" % version)

    def welcome(self, prog_name='taskcat.io'):
        banner = pyfiglet.Figlet(font='standard')
        self.banner = banner
        print("{0}".format(banner.renderText(prog_name), '\n'))
        self.checkforupdate()


def get_cfn_stack_events(self, stackname, region):
    """
    Given a stack name and the region, this function returns the event logs of the given stack, as list.
    :param self:
    :param stackname: Name of the stack
    :param region: Region stack belongs to
    :return: Event logs of the stack
    """
    cfn_client = self._boto_client.get('cloudformation', region)
    stack_events = []
    try:
        response = cfn_client.describe_stack_events(StackName=stackname)
        stack_events.extend(response['StackEvents'])
        while 'NextToken' in response:
            response = cfn_client.describe_stack_events(NextToken=response['NextToken'], StackName=stackname)
            stack_events.extend(response['StackEvents'])
    except ClientError as e:
        print("{} Error trying to get the events for stack [{}] in region [{}]\b {}".format(
            E,
            str(stackname),
            str(region),
            e
        ))
        # Commenting below line to avoid sudden exit on describe call failure. So that delete stack may continue.
        # sys.exit()

    return stack_events


def main():
    pass


if __name__ == '__main__':
    pass

else:
    main()
