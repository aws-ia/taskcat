#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:avattathil@gmail.com
# repo: https://avattathil/taskcat.io
# docs: http://taskcat.io
#
# taskcat is short for task (cloudformation automated testing)
# This program takes as input:
# cfn template and json formatted parameter input file
# inputs can be passed as cli for single test
# for more diverse scenarios you can use a yaml configuration
# Planed Features:
# - Tests in only specific regions
# - Email test results to owner of project

# --imports --
import os
import uuid
import sys
import pyfiglet
import argparse
import re
import boto3
import yaml
import json
import urllib
import textwrap
import random


# Version Tag
version = 'v.01'
debug = u'\u2691'.encode('utf8')
error = u'\u26a0'.encode('utf8')
check = u'\u2714'.encode('utf8')
fail = u'\u2718'.encode('utf8')
info = u'\u2139'.encode('utf8')
E = '[ERROR%s] :' % error
D = '[DEBUG%s] :' % debug
P = '[PASS %s] :' % check
F = '[FAIL %s] :' % fail
I = '[INFO %s] :' % info


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

    def __init__(self, nametag):
        self.nametag = nametag
        self.project = "not set"
        self.capabilities = []
        self.verbose = False
        self.config = 'config.yml'
        self.test_region = []
        self.s3bucket = "not set"
        self.template_path = "not set"
        self.parameter_path = "not set"
        self.defult_region = "us-west-2"
        self._template_file = "not set"
        self._parameter_path = "not set"
        self._termsize = 110
        self._banner = ""
        self._use_global = False
        self._password = "Notset"
        self.interface

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
        return self.s3bucket

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

    def s3upload(self, taskcat_cfg):
        print '-' * self._termsize
        print self.nametag + ": I uploaded the following assets"
        print '=' * self._termsize

        s3 = boto3.resource('s3')
        bucket = s3.Bucket(taskcat_cfg['global']['s3bucket'])
        self.set_s3bucket(bucket.name)
        project = taskcat_cfg['global']['project']
        self.set_project(project)
        if os.path.isdir(project):
            fsmap = buildmap('.', project)
        else:
            print "Cannot access directory [%s]" % project
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

        for buckets in s3.buckets.all():
            for obj in buckets.objects.filter(Prefix=project):
                o = str('{0}/{1}'.format(buckets.name, obj.key))
                print o

        print '-' * self._termsize

    def get_s3_url(self, key):
        s3root = "https://s3.amazonaws.com/"
        s3 = boto3.resource('s3')
        for buckets in s3.buckets.all():
            if self.verbose:
                print D + "Processing .... objects"
            for obj in buckets.objects.filter(Prefix=(self.get_project())):
                if key in obj.key:
                    path = (str('{0}/{1}'.format(buckets.name, obj.key)))
                    url = "{0}{1}".format(s3root, path)
                    return url

    def genpassword(self, passlength):
        plen = int(passlength)
        password = ''.join(random.sample(
            map(chr, range(48, 57) + range(65, 90) + range(97, 120)), plen))
        return password

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

    def validate_template(self, taskcat_cfg, test_list):
        # Load gobal regions
        self.set_test_region(self.get_global_region(taskcat_cfg))
        for test in test_list:
            print self.nametag + "| Validate Template in test[%s]" % test
            self.define_tests(taskcat_cfg, test)
            try:
                if self.verbose:
                    print D + "boto3 region [%s]" % self.get_default_region()
                cfnconnect = boto3.client(
                    'cloudformation', self.get_default_region())
                cfnconnect.validate_template(
                    TemplateURL=self.get_s3_url(self.get_template_file()))
                result = cfnconnect.validate_template(
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

    def stackcreate(self, taskcat_cfg, test_list, sprefix):
        stackids = []
        self.set_capabilities('CAPABILITY_IAM')
        for test in test_list:
            print self.nametag + "|Preparing to launch [%s]" % test
            id = str(uuid.uuid4())
            sname = re.sub(r'\W+', '', self.nametag)
            stackname = sname + '-' + sprefix + '-' + test + '-' + id[:4]
            self.define_tests(taskcat_cfg, test)
            for region in self.get_test_region():
                print I + "Preparing to launch in region [%s] " % region
                try:
                    cfnconnect = boto3.client('cloudformation', 'us-west-2')
                    s_parmsdata = urllib.urlopen(self.get_parameter_path())
                    s_parms = json.loads(s_parmsdata.read())
                    for parmdict in s_parms:
                        for keys in parmdict:
                            if re.search('\$\[\w+_genpass_\d{1,2}]',
                                         parmdict['ParameterValue']):
                                re.sub(
                                    '[^0-9]', '', parmdict['ParameterValue'])
                                parmdict[
                                    'ParameterValue'] = self.get_password(8)

                    if self.verbose:
                        print D + "Boto Connection region=%s" % region
                        print D + "StackName=" + stackname
                        print D + "DisableRollback=True"
                        print D + "TemplateURL=%s" % self.get_template_path()
                        print D + "Parameters=%s" % s_parms
                        print D + "Capabilities=%s" % self.get_capabilities()

                    stackdata = cfnconnect.create_stack(
                        StackName=stackname,
                        DisableRollback=True,
                        TemplateURL=self.get_template_path(),
                        Parameters=s_parms,
                        Capabilities=self.get_capabilities())
                    stackids.append(stackdata)

                except Exception as e:
                    if self.verbose:
                        print D + str(e)
                    sys.exit(F + "Cannot launch %s" % self.get_template_file())
            print "\t ....done"
        print '-' * self._termsize
        #print stackids
        return stackids

    def validate_json(self, jsonin):
        try:
            parms = json.load(jsonin)
            if self.verbose:
                print (json.dumps(parms, indent=4, separators=(',', ': ')))
        except ValueError:
            return False
        return True

    def validate_parameters(self, taskcat_cfg, test_list):
        for test in test_list:
            self.define_tests(taskcat_cfg, test)
            print self.nametag + "|Validate JSON input in test[%s]" % test
            if self.verbose:
                print D + "parameter_path = %s" % self.get_parameter_path()

            parms = urllib.urlopen(self.get_parameter_path())
            jsonstatus = self.validate_json(parms)

            if self.verbose:
                print D + "jsonstatus = %s" % jsonstatus

            if jsonstatus:
                print P + "Validated [%s]" % self.get_parameter_file()
            else:
                sys.exit(F + "Cannot validate %s" % self.get_parameter_file())

            print "\t ....done"
        print '-' * self._termsize
        return True

    def if_stackexists(self, stackname, region):
        cfnconnect = boto3.client('cloudformation', region)
        try:
            cfnconnect.describe_stacks(StackName=stackname)
            exists = "yes"
        except Exception as e:
            if self.verbose:
                print D + str(e)
                exists = "no"
        return exists

    def get_stackstatus(self, stackid):
        def regxfind(reobj, dataline):
            sg = reobj.search(dataline)
            if sg:
                return str(sg.group())
            else:
                return str('Not-found')

        region_re = re.compile('(?<=:)(.\w\-.+(\w*)\-\d)(?=:)')
        sname = re.sub(r'\W+', '', str(self.nametag))
        stack_pattern = sname + '-.*-(\w)*(?=/)'
        print stack_pattern
        stackname_re = re.compile(stack_pattern)
        region = regxfind(region_re, stackid)
        stackname = regxfind(stackname_re, stackid)
        testinfo = []
        cfnconnect = boto3.client('cloudformation', region)
        try:
            testquery = (cfnconnect.describe_stacks(StackName=stackname))
            for result in testquery['Stacks']:
                testinfo.append(stackname)
                testinfo.append(region)
                testinfo.append(result.get('StackStatus'))
                if result.get('StackStatus') == 'CREATE_IN_PROGRESS' or result.get('StackStatus') == 'DELETE_IN_PROGRESS':
                    testinfo.append(1)
                else:
                    testinfo.append(0)
        except Exception:
            testinfo.append(stackname)
            testinfo.append(region)
            testinfo.append("USER_DELETED")
            testinfo.append(0)
        return testinfo

    def define_tests(self, yamlc, test):
        for tdefs in yamlc['tests'].keys():
            # print "[DEBUG] tdefs = %s" % tdefs
            if tdefs == test:
                t = yamlc['tests'][test]['template_file']
                p = yamlc['tests'][test]['parameter_input']
                n = yamlc['global']['project']
                b = yamlc['global']['s3bucket']
                self.set_s3bucket(b)
                self.set_project(n)
                self.set_template_file(t)
                self.set_parameter_file(p)
                self.set_template_path(
                    self.get_s3_url(self.get_template_file()))
                self.set_parameter_path(
                    self.get_s3_url(self.get_parameter_file()))
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
                print self.nametag + ": AWS AccountNumber: \t [%s]" % account
                print self.nametag + ": Authenticated via: \t [boto-profile] "
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
                print self.nametag + ": AWS AccountNumber: \t [%s]" % account
                print self.nametag + ": Authenticated via: \t [role] "
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
                print self.nametag + ": AWS AccountNumber: \t [%s]" % account
                print self.nametag + ": Authenticated via: \t [role] "
            except Exception as e:
                print E + "Credential Error - Cannot assume role!"
                if self.verbose:
                    print D + str(e)
                sys.exit(1)

    def validate_yaml(self, yaml_file):
        # type: (object) -> object
        print '-' * self._termsize
        run_tests = []
        required_global_keys = ['s3bucket',
                                'project',
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
                        print I + " Queing test => %s " % defined
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
            print E + "yaml [%s] is not formated well!!" % yaml_file
            if self.verbose:
                print D + str(e)
            sys.exit(1)
        return run_tests

    @property
    def interface(self):
        parser = argparse.ArgumentParser(
            description='(Cloudformation Test Framework)',
            prog=__file__, prefix_chars='-')
        parser.add_argument(
            '-c',
            '--config_yml',
            type=str,
            help="[Configuration yaml] Read configuration from config.yml")
        parser.add_argument(
            '-b',
            '--s3bucket',
            type=str,
            help="s3 bucket for templates ")
        parser.add_argument(
            '-t',
            '--template',
            type=str,
            help="Filesystem Path to template or S3 location")
        parser.add_argument(
            '-m',
            '--marketplace',
            default='False',
            dest='marketplace',
            action='store_true')
        parser.add_argument(
            '-r',
            '--region',
            nargs='+',
            type=str,
            help="Specfiy a comma seprated list of region " +
            "(example: us-east-1, us-west-1, eu-west-1)")
        parser.add_argument(
            '-P',
            '--boto-profile',
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
            '-p',
            '--parms_file',
            type=str,
            help="Json Formated Input file")
        parser.add_argument(
            '-ey',
            '--example_yaml',
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

        if (args.config_yml is not None and
                args.template is not None or
                args.s3bucket is not None or
                args.region is not None):
            print E + "You specified a yaml config file for this test"
            nc = "-t (--template) -b (--test-bucket) -r (--region)"
            print " %s are not compatable with yaml mode." % nc
            print E + " Please remove these flags!"
            print " [INFO] For more info use help" + __file__ + " --help"
            print "        exiting...."
            sys.exit(1)

        if (args.template is not None and args.parms_file is None):
            parser.error("You specfied a template file with no parmeters!")
            print parser.print_help()
            sys.exit(1)
        elif args.template is None and args.parms_file is not None:
            parser.error("You specfied a parameter file with no template!")
            print parser.print_help()
            sys.exit(1)

        if args.boto_profile is not None:
            if (args.aws_access_key is not None or
                    args.aws_secret_key is not None):
                parser.error("Cannot use boto profile -P (--boto_profile)" +
                             "with --aws_access_key or --aws_secret_key")
                print parser.print_help()
                sys.exit(1)

        return args

    def welcome(self, prog_name):
        me = prog_name.replace('.py', ' ')
        banner = pyfiglet.Figlet(font='standard')
        self.banner = banner
        print banner.renderText(me)
        print "version %s" % version


def main():
    pass

if __name__ == '__main__':
    pass

else:
    main()
