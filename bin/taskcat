#!/usr/bin/env python
# authors:
# Tony Vattathil tonynv@amazon.com, avattathil@gmail.com
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh sshvans@amazon.com,
# Jay McConnell, jmmccon@amazon.com
"""
 Program License: Amazon License
 Python Class License: Apache 2.0
"""

from __future__ import print_function
import taskcat
import yaml
import sys
import os
import traceback


if sys.version_info[0] < 3:
    raise Exception("Please use Python 3")


def main():
    tcat_instance = taskcat.TaskCat()
    args = tcat_instance.interface
    tcat_instance.welcome('taskcat')
    # Initialize cli interface
    # :TODO Add RestFull Interface

    # Get configuration from command line arg (-c)
    tcat_instance.set_config(args.config_yml)
    # tcat_instance.set_config('ci/config.yml')
    # Get API Handle - Try all know auth
    tcat_instance.aws_api_init(args)
    # Optional: Enables verbose output by default (DEBUG ON)
    tcat_instance.verbose = True
# --Begin
# Check for valid ymal and required keys in config
    if args.config_yml is not None:

        test_list = tcat_instance.validate_yaml(args.config_yml)

# Load yaml into local taskcat config
        with open(tcat_instance.get_config(), 'r') as cfg:
            taskcat_cfg = yaml.safe_load(cfg.read())
        cfg.close()

        try:
            project_path = '/'.join(tcat_instance.get_config().split('/')[0:-3])
            if project_path:
                os.chdir(os.path.abspath(project_path))
                tcat_instance.lint(args.lint, path='/'.join(tcat_instance.get_config().split('/')[-3:-2]))
        except Exception as e:
            print("ERROR: Linting failed: %s" % e)
            if args.lint in ['error', 'strict']:
                raise
            else:
                traceback.print_exc()
        tcat_instance.stage_in_s3(taskcat_cfg)
        tcat_instance.validate_template(taskcat_cfg, test_list)
        tcat_instance.validate_parameters(taskcat_cfg, test_list)
        # instance.stackcreate returns testdata object
        testdata = tcat_instance.stackcreate(taskcat_cfg, test_list, args.stack_prefix)
        tcat_instance.get_stackstatus(testdata, 5)
        tcat_instance.createreport(testdata, 'index.html')
        tcat_instance.cleanup(testdata, 5)


# --End

main()
