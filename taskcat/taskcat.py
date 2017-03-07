#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil tonynv@amazon.com, avattathil@gmail.com
# Shivansh Singh sshvans@amazon.com,
# Santiago Cardenas sancard@amazon.com,
#
# repo: https://github.com/aws-quickstart/taskcat
# docs: https://aws-quickstart.github.io/taskcat/
#
# This program takes as input:
# cfn template and json formatted parameter input file
# To create tests define the test parmaterms in config.yml (Exmaple below)
# Planed Features:
# - Email test results to owner of project

# --imports --
import os
import uuid
import sys
import pyfiglet
import argparse
import re
import json
import urllib
import textwrap
import random
import time
import base64
import yaml
import yattag
import boto3
from botocore.client import Config


# Version Tag
version = '0.1.30'
debug = u'\u2691'.encode('utf8')
error = u'\u26a0'.encode('utf8')
check = u'\u2714'.encode('utf8')
fail = u'\u2718'.encode('utf8')
info = u'\u2139'.encode('utf8')
sig = base64.b64decode("dENhVA==")
id = str(uuid.uuid4())
E = '[ERROR %s ] :' % error
D = '[DEBUG %s ] :' % debug
P = '[PASS  %s ] :' % check
F = '[FAIL  %s ] :' % fail
I = '[INFO  %s ] :' % info


# Example config.yml
# --Begin
yaml_cfg = '''
global:
  notification: true
  owner: avattathil@gmail.com
  project: projectx
  reporting: true
  regions:
    - us-east-1
    - us-west-1
    - us-west-2
  report_email-to-owner: true
  report_publish-to-s3: true
  report_s3bucket: taskcat-reports
  s3bucket: projectx-templates
tests:
  projectx-senario-1:
    parameter_input: projectx-senario-1.json
    regions:
      - us-west-1
      - us-east-1
    template_file: projectx.template
  projetx-main-senario-all-regions:
    parameter_input: projectx-senario-all-regions.json
    template_file: projectx.template
'''
# --End
# Example config.yml

# Not implemented
# ------------------------------- System varibles
# --Begin
sys_yml = 'sys_config.yml'

# --End
# --------------------------------System varibles


def buildmap(start_location, mapstring):
    fs_map = []
    for fs_path, dirs, filelist in os.walk(start_location, topdown=False):
        for fs_file in filelist:
            fs_path_to_file = (os.path.join(fs_path, fs_file))
            if (mapstring in fs_path_to_file and
                    '.git' not in fs_path_to_file):
                fs_map.append(fs_path_to_file)
    return fs_map


# Task(Cat = Cloudformation automated Testing)
class TaskCat (object):

    def __init__(self, nametag='[TASKCAT ] '):
        self.nametag = nametag
        self.project = None
        self.capabilities = []
        self.verbose = False
        self.config = 'config.yml'
        self.test_region = []
        self.s3bucket = None
        self.template_path = None
        self.parameter_path = None
        self.defult_region = "us-west-2"
        self._template_file = None
        self._parameter_path = None
        self._termsize = 110
        self._banner = ""
        self._report = False
        self._use_global = False
        self._password = None
        self.run_cleanup = None

    def set_project(self, project):
        self.project = project

    def get_project(self):
        return self.project

    def set_capabilities(self, ability):
        self.capabilities.append(ability)

    def get_capabilities(self):
        return self.capabilities

    def set_s3bucket(self, bucket):
        self.s3bucket = bucket

    def get_s3bucket(self):
        return str(self.s3bucket)

    def set_config(self, config_yml):
        if os.path.isfile(config_yml):
            self.config = config_yml
        else:
            print "Cannot locate file %s" % config_yml
            exit(1)

    def get_config(self):
        return self.config

    def get_template_file(self):
        return self._template_file

    def set_template_file(self, template):
        self._template_file = template

    def set_parameter_file(self, parameter):
        self._parameter_file = parameter

    def get_parameter_file(self):
        return self._parameter_file

    def set_parameter_path(self, parameter):
        self.parameter_path = parameter

    def get_parameter_path(self):
        return self.parameter_path

    def set_template_path(self, template):
        self.template_path = template

    def get_template_path(self):
        return self.template_path

    def set_password(self, password):
        self._password = password

    def get_password(self):
        return self._password

    def set_default_region(self, region):
        self.defult_region = region

    def get_default_region(self):
        return (self.defult_region)

    def stage_in_s3(self, taskcat_cfg):
        print '-' * self._termsize
        print self.nametag + ":I uploaded the following assets"
        print '=' * self._termsize

        project = taskcat_cfg['global']['qsname']

        s3 = boto3.resource('s3')
        if 's3bucket' in taskcat_cfg['global'].keys():
            bucket = s3.Bucket(taskcat_cfg['global']['s3bucket'])
            print I + "Staging Bucket => " + bucket.name
            self.set_s3bucket(bucket.name)
        else:
            auto_bucket = 'taskcat-' + project + "-" + id[:8]
            print I + "Staging Bucket => " + auto_bucket
            s3.create_bucket(Bucket=auto_bucket)
            bucket = s3.Bucket(auto_bucket)
            self.set_s3bucket(bucket.name)

        self.set_project(project)
        if os.path.isdir(project):
            fsmap = buildmap('.', project)
        else:
            print "{0}!Cannot access directory {1}".format(
                E,
                project)

            sys.exit(1)

        for filename in fsmap:
            try:
                upload = re.sub('^./', '', filename)
                bucket.Acl().put(ACL='public-read')
                bucket.upload_file(filename,
                                   upload,
                                   ExtraArgs={'ACL': 'public-read'})
            except Exception as e:
                print "Cannot Upload to bucket => %s" % bucket.name
                print E + "Check that you bucketname is correct"
                if self.verbose:
                    print D + str(e)
                sys.exit(1)

        for obj in bucket.objects.all():
            o = str('{0}/{1}'.format(self.get_s3bucket(), obj.key))
            print o

        print '-' * self._termsize

    def get_available_azs(self, region, count):
        available_azs = []
        ec2_client = boto3.client('ec2', region_name=region)
        availability_zones = ec2_client.describe_availability_zones(
            Filters=[{'Name': 'state', 'Values': ['available']}])

        for az in availability_zones['AvailabilityZones']:
            available_azs.append(az['ZoneName'])

        if len(available_azs) < count:
            print "{0}!Only {1} az's are available in {2}".format(
                E,
                len(available_azs),
                region)
            quit()
        else:
            azs = ','.join(available_azs[:count])
            return azs

    def get_s3_url(self, key):
        client = boto3.client('s3',  config=Config(signature_version='s3v4'))
        bucket = self.get_s3bucket()

        bucket_location = client.get_bucket_location(
            Bucket=self.get_s3bucket())
        result = client.list_objects(Bucket=self.get_s3bucket(),
                                     Prefix=self.get_project())
        contents = result.get('Contents')
        for s3obj in contents:
            for metadata in s3obj.iteritems():
                if metadata[0] == 'Key':
                    if key in metadata[1]:
                        # Finding exact match
                        terms = metadata[1].split("/")
                        if key == terms[-1]:
                            if bucket_location[
                                'LocationConstraint'
                            ] is not None:
                                o_url = "https://s3-{0}.{1}/{2}/{3}".format(
                                    bucket_location['LocationConstraint'],
                                    "amazonaws.com",
                                    self.get_s3bucket(),
                                    metadata[1])
                                return o_url
                            else:
                                amzns3 = 's3.amazonaws.com'
                                o_url = "https://{0}/{1}/{2}".format(
                                    amzns3,
                                    self.get_s3bucket(),
                                    metadata[1])
                                return o_url

    def get_test_region(self):
        return self.test_region

    def set_test_region(self, region_list):
        self.test_region = []
        for region in region_list:
            self.test_region.append(region)

    def get_global_region(self, yamlcfg):
        g_regions = []
        for keys in yamlcfg['global'].keys():
            if 'region' in keys:
                try:
                    iter(yamlcfg['global']['regions'])
                    namespace = 'global'
                    for region in yamlcfg['global']['regions']:
                        # print "found region %s" % region
                        g_regions.append(region)
                        self._use_global = True
                except TypeError:
                    print "No regions defined in [%s]:" % namespace
                    print "Please correct region defs[%s]:" % namespace
        return g_regions

    def set_docleanup(self, cleanup_value):
        self.run_cleanup = cleanup_value

    def get_docleanup(self):
        return self.run_cleanup

    # Given a stackId, function returns the list of dictionary items, where each item
    # consist of logicalId, physicalId and resourceType of the aws resource associated
    # with the stack.
    #
    # Return object syntax:
    # [
    #     {
    #         'logicalId': 'string',
    #         'physicalId': 'string',
    #         'resourceType': 'String'
    #     },
    # ]
    def get_resources(self, stackId):
        l_resources = []
        try:
            cfn = boto3.client(
                'cloudformation', self.get_default_region())
            result = cfn.describe_stack_resources(
                StackName=stackId)
            stackResources = result.get('StackResources')
            for resource in stackResources:
                if self.verbose:
                    print "Resource: \
                    LogicalId = {0}, PhysicalId = {1}, Type = {2}".format(
                        resource.get('LogicalResourceId'),
                        resource.get('PhysicalResourceId'),
                        resource.get('ResourceType')
                    )
                d = {}
                d['logicalId'] = resource.get('LogicalResourceId')
                d['physicalId'] = resource.get('PhysicalResourceId')
                d['resourceType'] = resource.get('ResourceType')
                l_resources.append(d)
        except Exception as e:
            if self.verbose:
                print
                D + str(e)
            sys.exit(F + "Unable to get resources for stack %s" % stackId)
        print "\t ....done"
        return l_resources

    # Given a list of stackIds, function returns the list of dictionary items, where each
    # item consist of stackId and the resources associated with that stack.
    #
    # Return object syntax:
    # [
    #     {
    #         'stackId': 'string',
    #         'resources': [
    #             {
    #                'logicalId': 'string',
    #                'physicalId': 'string',
    #                'resourceType': 'String'
    #             },
    #         ]
    #     },
    # ]
    def get_all_resources(self, stackIds):
        l_all_resources = []
        for anId in stackIds:
            d = {}
            d['stackId'] = anId
            d['resources'] = self.get_resources(anId)
            l_all_resources.append(d)
            if self.verbose:
                print json.dumps(d)
        return l_all_resources

    def validate_template(self, taskcat_cfg, test_list):
        # Load global regions
        self.set_test_region(self.get_global_region(taskcat_cfg))
        for test in test_list:
            print self.nametag + ":Validate Template in test[%s]" % test
            self.define_tests(taskcat_cfg, test)
            try:
                if self.verbose:
                    print D + "default region [%s]" % self.get_default_region()
                cfn = boto3.client(
                    'cloudformation', self.get_default_region())
                cfn.validate_template(
                    TemplateURL=self.get_s3_url(self.get_template_file()))
                result = cfn.validate_template(
                    TemplateURL=self.get_s3_url(self.get_template_file()))
                print P + "Validated [%s]" % self.get_template_file()
                cfn_result = (result['Description'])
                print I + "Description  [%s]" % textwrap.fill(cfn_result)
                if self.verbose:
                    cfn_parms = json.dumps(
                        result['Parameters'],
                        indent=4,
                        separators=(',', ': '))
                    print D + "Parameters = %s" % cfn_parms
            except Exception as e:
                if self.verbose:
                    print D + str(e)
                sys.exit(F + "Cannot validate %s" % self.get_template_file())
            print "\t ....done"
        print '-' * self._termsize
        return True

    def genpassword(self, passlength, passtype):
        if passtype == 'A':
            plen = int(passlength)
            password = ''.join(random.sample(
                map(chr,
                    range(48, 57) +
                    range(65, 90) +
                    range(97, 120)
                    ), plen))
            return password

        elif type == 'S':
            plen = int(passlength)
            password = ''.join(random.sample(
                map(chr,
                    range(48, 57) +
                    range(65, 90) +
                    range(97, 120)
                    ), plen))
            return password + '@'
        else:
            plen = int(passlength)
            password = ''.join(random.sample(
                map(chr,
                    range(48, 57) +
                    range(65, 90) +
                    range(97, 120)
                    ), plen))
            return password + '@'

    def stackcreate(self, taskcat_cfg, test_list, sprefix):
        stackids = []
        self.set_capabilities('CAPABILITY_IAM')
        for test in test_list:
            print self.nametag + "|Preparing to launch [%s]" % test
            sname = str(sig)
            stackname = sname + '-' + sprefix + '-' + test + '-' + id[:4]
            self.define_tests(taskcat_cfg, test)
            for region in self.get_test_region():
                print I + "Preparing to launch in region [%s] " % region
                try:
                    cfn = boto3.client('cloudformation', region)
                    s_parmsdata = urllib.urlopen(self.get_parameter_path())
                    s_parms = json.loads(s_parmsdata.read())
                    for parmdict in s_parms:
                        for keys in parmdict:
                            param_value = parmdict['ParameterValue']
                            count_re = re.compile('\d+(?=])')
                            gentype_re = re.compile(
                                '(?!\w+_genpass-)[A|S](?=_\d{1,2}])')
                            genpass_re = re.compile(
                                '\$\[\w+_genpass-[A|S]_\d{1,2}]')
                            genaz_re = re.compile('\$\[\w+_genaz_\d{1}]')

                            if genpass_re.search(param_value):
                                passlen = int(
                                    self.regxfind(count_re, param_value))
                                gentype = self.regxfind(
                                    gentype_re, param_value)
                                if passlen:
                                    if self.verbose:
                                        print D + "Auto generating password"
                                        print D + "Pass size => {0}".format(
                                            passlen)
                                        print D + "Pass type => {0}".format(
                                            gentype)

                                    param_value = self.genpassword(
                                        passlen, gentype)
                                    parmdict['ParameterValue'] = param_value

                            if genaz_re.search(param_value):
                                numazs = int(
                                    self.regxfind(count_re, param_value))
                                if numazs:
                                    if self.verbose:
                                        print D + "Selecting availablity zones"
                                        print D + "Requested %s az's" % numazs

                                    param_value = self.get_available_azs(
                                        region,
                                        numazs)
                                    parmdict['ParameterValue'] = param_value
                                else:
                                    print E + "$[auto_genaz_(!)]"
                                    print I + "(Number of az's not specified!"
                                    print I + "Defaulting to 1 az)"
                                    param_value = self.get_available_azs(
                                        region,
                                        1)
                                    parmdict['ParameterValue'] = param_value

                    if self.verbose:
                        print D + "Creating Boto Connection region=%s" % region
                        print D + "StackName=" + stackname
                        print D + "DisableRollback=True"
                        print D + "TemplateURL=%s" % self.get_template_path()
                        print D + "Parameters=%s" % json.dumps(
                            s_parms,
                            sort_keys=True,
                            indent=4,
                            separators=(',', ': '))
                        print D + "Capabilities=%s" % self.get_capabilities()

                    stackdata = cfn.create_stack(
                        StackName=stackname,
                        DisableRollback=True,
                        TemplateURL=self.get_template_path(),
                        Parameters=s_parms,
                        Capabilities=self.get_capabilities())
                    stackids.append(stackdata)

                except Exception as e:
                    if self.verbose:
                        print E + str(e)
                    sys.exit(F + "Cannot launch %s" % self.get_template_file())
            print "\t ....done"
        print '-' * self._termsize
        for stack in stackids:
            created = str(stack['StackId']).split('/')
            arn = created[0].split(':stack', 1)[0]
            print self.nametag + "| >> LAUNCHING STACKS <<"
            print I + "|arn = %s " % arn

        return stackids

    def validate_json(self, jsonin):
        try:
            parms = json.load(jsonin)
            if self.verbose:
                print(json.dumps(parms, indent=4, separators=(',', ': ')))
        except ValueError as e:
            print E + str(e)
            return False
        return True

    def validate_parameters(self, taskcat_cfg, test_list):
        for test in test_list:
            self.define_tests(taskcat_cfg, test)
            print self.nametag + "|Validate JSON input in test[%s]" % test
            if self.verbose:
                print D + "parameter_path = %s" % self.get_parameter_path()

            inputparms = urllib.urlopen(self.get_parameter_path())
            jsonstatus = self.validate_json(inputparms)

            if self.verbose:
                print D + "jsonstatus = %s" % jsonstatus

            if jsonstatus:
                print P + "Validated [%s]" % self.get_parameter_file()
            else:
                print D + "parameter_file = %s" % self.get_parameter_file()
                sys.exit(F + "Cannot validate %s" % self.get_parameter_file())

            print "\t ....done"
        print '-' * self._termsize
        return True

    def regxfind(self, re_object, dataline):
        sg = re_object.search(dataline)
        if sg:
            return str(sg.group())
        else:
            return str('Not-found')

    def parse_stack_info(self, stack_id):
        stack_info = dict()

        region_re = re.compile('(?<=:)(.\w-.+(\w*)\-\d)(?=:)')
        stack_name_re = re.compile('(?<=:stack/)(tCaT.*.)(?=/)')
        stack_info['region'] = self.regxfind(region_re, stack_id)
        stack_info['stack_name'] = self.regxfind(stack_name_re, stack_id)
        return stack_info

    def stackcheck(self, stack_id):
        stackdata = self.parse_stack_info(stack_id)
        region = stackdata['region']
        stack_name = stackdata['stack_name']
        test_info = []
        cfn = boto3.client('cloudformation', region)
        try:
            test_query = (cfn.describe_stacks(StackName=stack_name))
            for result in test_query['Stacks']:
                test_info.append(stack_name)
                test_info.append(region)
                test_info.append(result.get('StackStatus'))
                if result.get(
                        'StackStatus') == 'CREATE_IN_PROGRESS' or result.get(
                        'StackStatus') == 'DELETE_IN_PROGRESS':
                    test_info.append(1)
                else:
                    test_info.append(0)
        except Exception:
            test_info.append(stack_name)
            test_info.append(region)
            test_info.append("STACK_DELETED")
            test_info.append(0)
        return test_info

    def get_stackstatus(self, stackids, speed):
        active_tests = 1
        while (active_tests > 0):
            current_active_tests = 0
            for stack in stackids:
                stackquery = self.stackcheck(stack['StackId'])
                current_active_tests = stackquery[3] + current_active_tests
                print I + "[{0}]  \t|{1}|\t   [{2}]".format(
                    stackquery[0],
                    stackquery[1],
                    stackquery[2])
                active_tests = current_active_tests
                time.sleep(speed)

    def cleanup(self, stackids, speed):
        docleanup = self.get_docleanup()
        if self.verbose:
            print D + "clean-up = %s " % str(docleanup)

        if docleanup:
            stackidtodelete = stackids
            print self.nametag + "| >> CLEANUP STACKS <<"
            for stack in stackidtodelete:
                self.stackdelete(stack['StackId'])
            self.get_stackstatus(stackids, speed)
        else:
            print I + "[Retaining Stacks (Cleanup is set to {0}]".format(
                docleanup)

    def stackdelete(self, stack_id):
        stackdata = self.parse_stack_info(stack_id)
        region = stackdata['region']
        stack_name = stackdata['stack_name']
        cfn = boto3.client('cloudformation', region)
        cfn.delete_stack(StackName=stack_name)

    def if_stackexists(self, stackname, region):
        exists = None
        cfn = boto3.client('cloudformation', region)
        try:
            cfn.describe_stacks(StackName=stackname)
            exists = "yes"
        except Exception as e:
            if self.verbose:
                print D + str(e)
                exists = "no"
        print I + "Successfully Deleted[%s]" % stackname
        return exists

    def define_tests(self, yamlc, test):
        for tdefs in yamlc['tests'].keys():
            # print "[DEBUG] tdefs = %s" % tdefs
            if tdefs == test:
                t = yamlc['tests'][test]['template_file']
                p = yamlc['tests'][test]['parameter_input']
                n = yamlc['global']['qsname']
                b = self.get_s3bucket()

                # Checks if cleanup flag is set
                # If cleanup is set to 'false' stack will not be deleted after
                # launch attempt
                if 'cleanup' in yamlc['global'].keys():
                    cleanupstack = yamlc['global']['cleanup']
                    if cleanupstack:
                        if self.verbose:
                            print D + "cleanup set to ymal value"
                            self.set_docleanup(cleanupstack)
                    else:
                        print I + "Cleanup value set to (false)"
                        self.set_docleanup(False)
                else:
                    # By default do cleanup unless self.run_cleanup
                    # was overwridden (set to False) by -n flag
                    if self.run_cleanup == False:
                        if self.verbose:
                            print D + "cleanup set by cli flag {0}".format(
                                self.run_cleanup)
                    else:
                        self.set_docleanup(True)
                        print I + "No cleanup value set (default to cleanup)"

                # Load test setting
                self.set_s3bucket(b)
                self.set_project(n)
                self.set_template_file(t)
                self.set_parameter_file(p)
                self.set_template_path(
                    self.get_s3_url(self.get_template_file()))
                self.set_parameter_path(
                    self.get_s3_url(self.get_parameter_file()))

                # Check to make sure template filenames are correct
                template_path = self.get_template_path()
                if not template_path:
                    print "{0} Could not locate {1}".format(
                        E,
                        self.get_template_file())
                    print "{0} Check to make sure filename is correct?".format(
                        E,
                        self.get_parameter_file())
                    quit()

                # Check to make sure parameter filenames are correct
                parameter_path = self.get_parameter_path()
                if not parameter_path:
                    print "{0} Could not locate {1}".format(
                        E,
                        self.get_parameter_file())
                    print "{0} Check to make sure filename is correct?".format(
                        E,
                        self.get_parameter_file())
                    quit()

                if self.verbose:
                    print I + "(Acquiring) tests assets for .......[%s]" % test
                    print D + "|S3 Bucket  => [%s]" % self.get_s3bucket()
                    print D + "|Project    => [%s]" % self.get_project()
                    print D + "|Template   => [%s]" % self.get_template_path()
                    print D + "|Parameter  => [%s]" % self.get_parameter_path()
                if 'regions' in yamlc['tests'][test]:
                    if yamlc['tests'][test]['regions'] is not None:
                        r = yamlc['tests'][test]['regions']
                        self.set_test_region(list(r))
                        if self.verbose:
                            print D + "|Defined Regions:"
                            for list_o in self.get_test_region():
                                print "\t\t\t - [%s]" % list_o
                else:
                    global_regions = self.get_global_region(yamlc)
                    self.set_test_region(list(global_regions))
                    if self.verbose:
                        print D + "|Global Regions:"
                        for list_o in self.get_test_region():
                            print "\t\t\t - [%s]" % list_o
                if self.verbose:
                    print I + "(Completed) acquisition of [%s]" % test

    # Set AWS Credentials
    def aws_api_init(self, args):
        print '-' * self._termsize
        if args.boto_profile:
            boto3.setup_default_session(profile_name=args.boto_profile)
            try:
                sts_client = boto3.client('sts')
                account = sts_client.get_caller_identity().get('Account')
                print self.nametag + ":AWS AccountNumber: \t [%s]" % account
                print self.nametag + ":Authenticated via: \t [boto-profile] "
            except Exception as e:
                print E + "Credential Error - Please check you profile!"
                if self.verbose:
                    print D + str(e)
                sys.exit(1)
        elif args.aws_access_key and args.aws_secret_key:
            boto3.setup_default_session(
                aws_access_key_id=args.aws_access_key,
                aws_secret_access_key=args.aws_secret_key)
            try:
                sts_client = boto3.client('sts')
                account = sts_client.get_caller_identity().get('Account')
                print self.nametag + ":AWS AccountNumber: \t [%s]" % account
                print self.nametag + ":Authenticated via: \t [role] "
            except Exception as e:
                print E + "Credential Error - Please check you keys!"
                if self.verbose:
                    print D + str(e)
                sys.exit(1)
        else:
            boto3.setup_default_session(
                aws_access_key_id=args.aws_access_key,
                aws_secret_access_key=args.aws_secret_key)
            try:
                sts_client = boto3.client('sts')
                account = sts_client.get_caller_identity().get('Account')
                print self.nametag + ":AWS AccountNumber: \t [%s]" % account
                print self.nametag + ":Authenticated via: \t [role] "
            except Exception as e:
                print E + "Credential Error - Cannot assume role!"
                if self.verbose:
                    print D + str(e)
                sys.exit(1)

    def validate_yaml(self, yaml_file):
        # type: (object) -> object
        print '-' * self._termsize
        run_tests = []
        required_global_keys = ['qsname',
                                'owner',
                                'reporting',
                                'regions']

        required_test_parameters = ['template_file',
                                    'parameter_input']
        try:
            if os.path.isfile(yaml_file):
                with open(yaml_file, 'r') as checkyaml:
                    cfg_yml = yaml.load(checkyaml.read())
                    for key in required_global_keys:
                        if key in cfg_yml['global'].keys():
                            pass
                        else:
                            print "global:%s missing from " % key + yaml_file
                            sys.exit(1)

                    for defined in cfg_yml['tests'].keys():
                        run_tests.append(defined)
                        print self.nametag + "|Queing test => %s " % defined
                        for parms in cfg_yml['tests'][defined].keys():
                            for key in required_test_parameters:
                                if key in cfg_yml['tests'][defined].keys():
                                    pass
                                else:
                                    print "No key %s in test" % key + defined
                                    print E + "While inspecting: " + parms
                                    sys.exit(1)
            else:
                print E + "Cannot open [%s]" % yaml_file
                sys.exit(1)
        except Exception as e:
            print E + "config.yml [%s] is not formated well!!" % yaml_file
            if self.verbose:
                print D + str(e)
            sys.exit(1)
        return run_tests

    def genreport(self, test_list, stackids):
        doc = yattag.Doc()

        def getofile():
            location = "somefile.log"
            return str(location)

        tag = doc.tag
        text = doc.text
        logo = 'taskcat'
        repo_link = 'https://github.com/aws-quickstart/taskcat'
        output_css = 'https://taskcat.s3.amazonaws.com/assets/css/taskcat.css'
        doc_link = 'http://taskcat.io'
        footer = 'Report Generated by TaskCat'

        with tag('html'):
            with tag('head'):
                doc.stag('meta', charset='utf-8')
                doc.stag(
                    'meta', name="viewport", content="width=device-width")
                doc.stag('link', rel='stylesheet',
                         href=output_css)
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

                        for test in test_list:
                            print "Generating Report for test [%s]" % test
                            report_data = {}
                            test_data = []
                            for _stack in stackids:
                                stackid = _stack['StackId']
                                stack_info = self.parse_stack_info(stackid)
                                stackname = stack_info['stack_name']
                                region = stack_info['region']

                                if test in stackname:
                                    test_data.append(region)
                                    test_data.append(stackname)
                                    report_data = {test: test_data}

                                    for _t, _tdata in report_data.items():
                                        testname = _t
                                        region = _tdata[0]
                                        stackname = _tdata[1]

                                        if self.verbose:
                                            print D + "Recording stack {0} \
                                                    in test {1}".format(
                                                stackname, testname)

                                        cfn = boto3.client(
                                            'cloudformation', region)
                                        test_query = cfn.describe_stacks(
                                            StackName=stackname)

                                        for result in test_query['Stacks']:
                                            _status = result.get(
                                                'StackStatus')
                                            if _status == 'CREATE_COMPLETE':
                                                status_css = 'class=test-green'
                                            elif _status == 'CREATE_FAILED':
                                                status_css = 'class=test-red'
                                            else:
                                                status_css = 'class=test-red'

                                            with tag('tr'):
                                                with tag('td',
                                                         'class=test-info'):
                                                    with tag('h3'):
                                                        text(testname)
                                                with tag('td',
                                                         'class=text-left'):
                                                    text(region)
                                                with tag('td',
                                                         'class=text-left'):
                                                    text(stackname)
                                                with tag('td',
                                                         status_css):
                                                    text(str(_status))
                                                with tag('td',
                                                         'class=text-left'):
                                                    with tag('a',
                                                             href=getofile()):
                                                        text('View Logs')

                                            if lastreport == testname:
                                                print "Completed report for %s" % stackname
                                                lastreport = testname
                                            else:
                                                lastreport = testname
                                                with tag('tr',
                                                         'class= test-footer'):
                                                    with tag('td',
                                                             'colspan=5'):
                                                        text('')
                        doc.stag('p')

        indent = yattag.indent(doc.getvalue(),
                               indentation='    ',
                               newline='\r\n',
                               indent_text=True)
        return indent

    def createreport(self, test_list, stackids, filename):
        #@TODO:
        # Check for .html extenstion
        # write to outputs dir
        # push up to s3 optional

        print self.nametag + ">> GENERATING REPORTS <<"
        print I + "Writing report to [%s]" % filename
        logpath = filename
        file = open(logpath, 'w')
        file.write(
            self.genreport(test_list, stackids))
        file.close()

    @property
    def interface(self):
        parser = argparse.ArgumentParser(
            description='(Multi-Region Cloudformation  Deployment)',
            # prog=__file__, prefix_chars='-')
            prog='taskcat', prefix_chars='-')
        parser.add_argument(
            '-c',
            '--config_yml',
            type=str,
            help="[Configuration yaml] Read configuration from config.yml")
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
            help="AWS Secrect Key")
        parser.add_argument(
            '-ey',
            '--example_yaml',
            action='store_true',
            help="Print out example yaml")
        parser.add_argument(
            '-n',
            '--no_cleanup',
            action='store_true',
            help="Print out example yaml")
        parser.add_argument(
            '-v',
            '--verbose',
            action='store_true',
            help="Enables verbosity")

        args = parser.parse_args()

        if len(sys.argv) == 1:
            print parser.print_help()
            sys.exit(0)

        if args.example_yaml:
            print "#An example: config.yml file to be used with %s " % __name__
            print yaml_cfg
            sys.exit(0)

        if args.verbose:
            self.verbose = True
        # Overwrides Defaults for cleanup but does not overwrite config.yml
        if args.no_cleanup:
            self.run_cleanup = False

        if args.boto_profile is not None:
            if (args.aws_access_key is not None or
                    args.aws_secret_key is not None):
                parser.error("Cannot use boto profile -P (--boto_profile)" +
                             "with --aws_access_key or --aws_secret_key")
                print parser.print_help()
                sys.exit(1)

        return args

    def welcome(self, prog_name='taskcat.io'):
        banner = pyfiglet.Figlet(font='standard')
        self.banner = banner
        print banner.renderText(prog_name)
        print "version %s" % version


def main():
    pass

if __name__ == '__main__':
    pass

else:
    main()
