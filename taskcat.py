#!/usr/bin/env python
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
import sys
import pyfiglet
import argparse
import re
import boto3
import yaml
import json
import urllib


# Version Tag
version = 'v.01'

# Example config.yml
# --Begin
yaml_cfg = '''
global:
  notification: true
  owner: avattathil@gmail.com
  project: projectx
  regions:
    - us-east-1
    - us-west-1
    - us-west-2
  report_email-to-owner: true
  report_publish-to-s3: true
  report_s3bucket: taskcat-reports
  s3bucket: taskcat-testing
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
        self.config = 'config.yml'
        self.template_type = "unknown"
        self.test_region = ['none']
        self.s3bucket = "not set"
        self._template_path = "not set"
        self._parameter_file = "not set"
        self._termsize = 110
        self.interface()

    def set_project(self, project):
        self.project = project

    def get_project(self):
        return self.project

    def set_s3bucket(self, bucket):
        self.s3bucket = bucket

    def get_s3bucket(self):
        return self.s3bucket

    def set_config(self, config_yml):
        config_yml
        if os.path.isfile(config_yml):
            self.config = config_yml
        else:
            print "Cannot locate file %s" % config_yml
            exit

    def get_config(self):
        return self.config

    def get_template(self):
        return self._template_path

    def set_parameter(self, parameter):
        self._parameter_file = parameter

    def set_template(self, template):
        self._template_path = template
        if "https://s3" in self._template_path:
            # print "template type = [s3_object]"
            self.template_type = "s3_object"
        else:
            # print "template type = [local_file]"
            self.template_type = "local_file"

    def get_parameter(self):
        return self._parameter_file

    def s3upload(self, taskcat_cfg):
        print '-' * self._termsize
        print self.nametag + ": I uploaded the following assets"
        print '=' * self._termsize

        s3 = boto3.resource('s3')
        bucket = s3.Bucket(taskcat_cfg['global']['s3bucket'])
        bucket.Acl().put(ACL='public-read')
        self.set_s3bucket(bucket.name)
        project = taskcat_cfg['global']['project']
        self.set_project(project)
        if (os.path.isdir(project)):
            fsmap = buildmap('.', project)
        else:
            print "Cannot access directory [%s]" % project
            sys.exit(1)

        for filename in fsmap:
            # print "Obj =  %s" % filename
            # upload = re.sub('^./quickstart-', '', name)
            upload = re.sub('^./', '', filename)
            bucket.upload_file(filename,
                               upload,
                               ExtraArgs={'ACL': 'public-read'})

        for buckets in s3.buckets.all():
            # sname = re.sub('^./quickstart-', '', project)
            for obj in buckets.objects.filter(Prefix=project):
                o = str('{0}/{1}'.format(buckets.name, obj.key))
                print o
                #url = self.get_s3_url(bucket.name, obj.key)
                #print url

        print '-' * self._termsize

    #def getbucket(self, bucket, key):
    #   s3 = boto3.client('s3')
    #   url = '{}/{}/{}'.format(s3.meta.endpoint_url, bucket, key)
    #   return str(url)

    def get_s3_url(self, bucket, key):

        url = key
        s3 = boto3.resource('s3')
        for buckets in s3.buckets.all():
            # sname = re.sub('^./quickstart-', '', project)
            for obj in buckets.objects.filter(Prefix=(key)):
                print obj
                url = (str('{0}/{1}'.format(buckets.name, obj.key)))
                #print (self.getbucket(buckets.name, obj.key))
                #url = (self.getbucket(buckets.name, obj.key))
                print "URL === %s" % url
        return (url)

    def get_test_region(self):
        return self.test_region

    def set_test_region(self, region_list):
        self.test_region = []
        self.test_region.append (region_list)
        return region_list

    def get_global_region(self, yaml_cfg):
        g_regions = []
        for keys in yaml_cfg['global'].keys():
            if 'region' in keys:
                # print self.nametag + ":[DEBUG] Global Regions [%s]" % keys
                try:
                    iter(yaml_cfg['global']['regions'])
                    namespace = 'global'
                    for region in yaml_cfg['global']['regions']:
                        # print "found region %s" % region
                        g_regions.append(region)
                except TypeError:
                    print "No regions defined in [%s]:" % namespace
                    print "Please correct region defs[%s]:" % namespace
        return g_regions

    def validate_template(self, taskcat_cfg, test_list):
        # Load gobal regions
        print "--test--"
        self.set_test_region(self.get_global_region(taskcat_cfg))
        print (self.get_test_region())
        for test in test_list:
            print self.nametag + "|Validate Template in test[%s]" % test
            self.define_tests(taskcat_cfg, test)
            print (self.get_template())
            #try:
            #   cfnconnect = boto3.client('cloudformation')
            #    cfnconnect.validate_template(TemplateURL=self.get_template())
            #except Exception as e:
            #    print "[DEBUG]", e
            #   sys.exit("[FATAL] : Cannot read from %s" % self.get_template())
            #else:
             #   print"[PASS]: Template Validation Successful!"
              #  print self.nametag
              #  print ("Your template looks stupendous."
              #         " Allow me to continue...\n")
#              #  parms = urllib.urlopen(self._parameter_file)
#                print "Performing validation json parameter: " + parms
##                jsonstatus = self.validate_json(parms.read())
#                if jsonstatus:
# print "[PASS]: Parameters valid [continuing]"
#                    print self.nametag + "Parameters provided are perfect!!"
#                else:
#                    print self.nametag + "Yo, These parameters are whack son!!"
#                    sys.exit("[FATAL]:" + test + " is not valid [failed test]")

    def validate_json(jsonparms):
        try:
            json.loads(jsonparms)
        except ValueError:
            return False
        return True

    def define_tests(self, yaml_cfg, test):
        for tdefs in yaml_cfg['tests'].keys():
            # print "[DEBUG] tdefs = %s" % tdefs
            if tdefs == test:
                t = yaml_cfg['tests'][test]['template_file']
                p = yaml_cfg['tests'][test]['parameter_input']
                n = yaml_cfg['global']['project']
                b = yaml_cfg['global']['s3bucket']
                self.set_s3bucket(b)
                self.set_project(n)
                self.set_template(self.get_s3_url(b, t))
                self.set_parameter(self.get_s3_url(b, p))
                print "Defining Tests [S]...."
                print "\t |S3 Bucket        => [%s]" % self.get_s3bucket()
                print "\t |Project Name     => [%s]" % self.get_project()
                print "\t |Template Path    => [%s]" % self.get_template()
                print "\t |Parameter Path   => [%s]" % self.get_parameter()
                if 'regions' in yaml_cfg['tests'][test]:
                    if yaml_cfg['tests'][test]['regions'] is not None:
                        r = yaml_cfg['tests'][test]['regions']
                        print "r ---%s " % r
                        self.set_test_region(r)
                        print "\t |Defined Regions:"
                        for r_region in (self.get_test_region()):
                            print "\t\t\t - [%s]" % r_region
                else:
                    global_regions = self.get_global_region(yaml_cfg)
                    self.set_test_region(global_regions)
                    print "\t |Global Regions:"
                    print "\t\t\t - [%s]" % self.get_test_region()
                print "Defining Tests [E]...."

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
                print "[ERROR] Credential Error - Please check you profile!"
                print "[DEBUG]", e
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
                print "[ERROR] Credential Error - Please check you keys!"
                print "[DEBUG]", e
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
                print "[ERROR] Credential Error - Cannot assume role!"
                print "[DEBUG]", e
                sys.exit(1)

    def validate_yaml(self, yaml_file):
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
                        print "Queing test => %s " % defined
                        for parms in cfg_yml['tests'][defined].keys():
                            for key in required_test_parameters:
                                if key in cfg_yml['tests'][defined].keys():
                                    pass
                                else:
                                    print "No key %s in test" % key + defined
                                    print "[ERROR] while inspecting: " + parms
                                    sys.exit(1)
            else:
                print "[ERROR]Cannot open [%s]" % yaml_file
                sys.exit(1)
        except Exception as e:
            print "[ERROR] yaml [%s] is not formated well!!" % yaml_file
            print "[DEBUG]", e
            return False
        return run_tests

    def interface(self):
        parser = argparse.ArgumentParser(
            description='(Cloudformation Test Framework)',
            prog=__file__, prefix_chars='-')
        parser.add_argument(
            '-c',
            '--config_yml',
            type=str,
            help="[Configuration yaml] Read configuration from alfred.yml")
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
            dest='marketplace',
            action='store_true')
        parser.set_defaults(feature=False)
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

        args = parser.parse_args()

        if len(sys.argv) == 1:
            print parser.print_help()
            sys.exit(0)

        if args.example_yaml:
            print "An example: config.yml file to be used with %s " % __name__
            print yaml_cfg
            sys.exit(0)

        if (args.config_yml is not None and
                args.template is not None or
                args.s3bucket is not None or
                args.region is not None):
            print "[ERROR] You specified a yaml config file for this test"
            nc = "-t (--template) -b (--test-bucket) -r (--region)"
            print "[ERROR] %s are not compatable with yaml mode." % nc
            print "[ERROR] Please remove these flags!"
            print " [INFO] For more info use help" + __file__ + " --help"
            print "        exiting...."
            sys.exit(1)

        if (args.template is not None and args.parms_file is None):
            parser.error("You specfied a template file with no parmeters!")
            print parser.print_help()
            sys.exit(1)
        elif (args.template is None and args.parms_file is not None):
            parser.error("You specfied a parameter file with no template!")
            print parser.print_help()
            sys.exit(1)

        if (args.boto_profile is not None):
            if (args.aws_access_key is not None or
                    args.aws_secret_key is not None):
                parser.error("Cannot use boto profile -P (--boto_profile)" +
                             "with --aws_access_key or --aws_secret_key")
                print parser.print_help()
                sys.exit(1)

        return args

    def welcome():
        prog_name = os.path.basename(__file__)
        me = prog_name.replace('.py', ' ')
        banner = pyfiglet.Figlet(font='standard')
        print banner.renderText(me)
        print "version %s" % version


def main():
    pass

if __name__ == '__main__':
    pass

else:
    main()
