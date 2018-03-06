#!/usr/bin/env python
# authors:
# Tony Vattathil tonynv@amazon.com, avattathil@gmail.com
# Shivansh Singh sshvans@amazon.com,
# Santiago Cardenas sancard@amazon.com,
# Jay McConnell, jmmccon@amazon.com
"""
 Program License: Amazon License
 Python Class License: Apache 2.0
"""

from __future__ import print_function
import taskcat
import yaml
import sys

if sys.version_info[0] < 3:
    raise Exception("Please use Python 3")

def main():
    tcat_instance = taskcat.TaskCat()
    tcat_instance.welcome('taskcat')
    # Initialize cli interface
    # :TODO Add RestFull Interface
    args = tcat_instance.interface

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

        tcat_instance.stage_in_s3(taskcat_cfg)
        tcat_instance.validate_template(taskcat_cfg, test_list)
        tcat_instance.validate_parameters(taskcat_cfg, test_list)
        # instance.stackcreate returns testdata object
        # 'tag' can be replace with only alphanumeric values
        testdata = tcat_instance.stackcreate(taskcat_cfg, test_list, 'tag')
        tcat_instance.get_stackstatus(testdata, 5)
        tcat_instance.createreport(testdata, 'index.html')
        tcat_instance.cleanup(testdata, 5)


# --End

main()
