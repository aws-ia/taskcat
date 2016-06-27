#!/usr/bin/env python
# authors:avattathil@gmail.com
# repo: https://avattathil/taskcat.io
# docs: http://taskcat.io
#
# taskcat is short for task (cloudformation automated testing)
# This program takes as input:
# cfn template and json formated parameter input file
# inputs can be passed as cli for single test
# for more diverse scenarios you can use a ymal configuration
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

# Version Tag
version = 'v.01'

# Example config.yml
# --Begin
ymal = '''
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
  report_s3bucket: "s3:/taskcat-reports"
  template_s3bucket: "s3://taskcat-testing"
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
prog_name = os.path.basename(__file__)
me = prog_name.replace('.py', ' ')
# --End
# --------------------------------System varibles

parser = argparse.ArgumentParser(
    description='Alfred (Cloudformation Test Framework)',
    prog='alfred.py', prefix_chars='-')
parser.add_argument(
    '-c',
    '--config_yml',
    type=str,
    help="[Configuration ymal] Read configuration from alfred.yml")
parser.add_argument(
    '-b',
    '--test_bucket',
    type=str,
    help="s3 bucket to used to stage templates only needed with local files")
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
    help="Specfiy a comma seprated list of region where tests should run" +
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
    '--example_ymal',
    action='store_true',
    help="Print out example ymal")


def interface(args):
    if len(sys.argv) == 1:
        print parser.print_help()
        sys.exit(0)

    if args.example_ymal:
        print "An example: config.yml file to be used with %s " % __name__
        print ymal
        sys.exit(0)

    if (args.config_yml is not None and
        args.template is not None or
        args.test_bucket is not None or
            args.region is not None):
        print "[ERROR] You specified a ymal config file for this test"
        nc = "-t (--template) -b (--test-bucket) -r (--region)"
        print "[ERROR] %s are not compatable with ymal mode." % nc
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
                         "with -a (--aws_access_key or -s (--aws_secret_key")
            print parser.print_help()
            sys.exit(1)
    return args


# Core Fuctions
def regxfind(reobj, dataline):
    sg = reobj.search(dataline)
    if (sg):
        return str(sg.group())
    else:
        return str('Not-found')


# Task(Cat = Cloudformation automated Testing)
class TaskCat (object):

    def __init__(self, config_yml):
        self.template_type = "unknown"
        self._template_path = "not set"
        self._parameter_file = "not set"
        self.template_location = "not set"
        self.parameter_location = "not set"
        self.yml_cfg = "not set"
        self._termsize = 110
        if os.path.isfile(config_yml):
            self.yml_cfg = config_yml
        else:
            print "Cannot Read %s" % config_yml

    def buildmap(self, start_location, mapstring):
        fsmap = []
        for fpath, dirs, filelist in os.walk(start_location, topdown=False):
            for file in filelist:
                fullpath_to_file = (os.path.join(fpath, file))
                if (mapstring in fullpath_to_file and
                   '.git' not in fullpath_to_file):
                    fsmap.append(fullpath_to_file)
        return fsmap

    def get_template(self):
        return self._template_path

    def set_parameter(self, parameter):
        self._parameter_file = parameter

    def set_marketplace(self, ismarketplace):
        self._marketplace_ami = ismarketplace

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

    def get_maketplace(self):
        return self._marketplace_ami

    def s3upload(self, alfred_cfg):
        print '-' * self._termsize
        print "__alfred__: I uploaded the following assets"
        print '=' * self._termsize

        s3 = boto3.resource('s3')
        bucket = s3.Bucket(alfred_cfg['global']['s3bucket'])
        qsname = alfred_cfg['global']['qsname']
        fsmap = self.buildmap('.', qsname)
        for name in fsmap:
            # upload = re.sub('^./quickstart-', '', name)
            upload = re.sub('^./', '', name)
            bucket.upload_file(name, upload)

        for buckets in s3.buckets.all():
            # sname = re.sub('^./quickstart-', '', qsname)
            for obj in buckets.objects.filter(Prefix=qsname):
                o = "s3://" + str('{0}/{1}'.format(buckets.name, obj.key))
                print o

        print '-' * self._termsize


def direct():
    banner = pyfiglet.Figlet(font='standard')
    print banner.renderText(me)
    print "version %s" % version
    args = parser.parse_args()
    interface(args)


def main():
    pass
if __name__ == '__main__':
	pass
#    direct()

else:
    print "importing taskcat.io"
    print "to create a new taskcat"
    main()
