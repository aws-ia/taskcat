#!/usr/bin/env python
# authors:
# Tony Vattathil tonynv@amazon.com, avattathil@gmail.com
# Shivansh Singh sshvans@amazon.com,
# Santiago Cardenas sancard@amazon.com,
"""
 Program License: Amazon License
 Python Class License: Apache 2.0
"""

from __future__ import print_function
import taskcat
import yaml


def main():
    tcat_instance = taskcat.TaskCat()
    tcat_instance.welcome('taskcat')
    # Initalize cli interface
    # @TODO Add RestFull Interface
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

# Load ymal into local taskcat config
        with open(tcat_instance.get_config(), 'r') as cfg:
            taskcat_cfg = yaml.safe_load(cfg.read())
        cfg.close()

        tcat_instance.stage_in_s3(taskcat_cfg)
        tcat_instance.validate_template(taskcat_cfg, test_list)
        tcat_instance.validate_parameters(taskcat_cfg, test_list)
        testdata = tcat_instance.stackcreate(taskcat_cfg, test_list, 'tag')
        # Tracks test results in DynamoDb (only used for TaaS)
        tcat_instance.enable_dynamodb_reporting(True)
        tcat_instance.get_stackstatus(testdata, 5)
        tcat_instance.createreport(testdata, 'index.html')
        tcat_instance.cleanup(testdata, 5)


# --End

main()
