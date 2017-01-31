#!/usr/bin/env python
# authors: tonynv@amazon.com,sancard@amazon.com,sshvans@amazon.com
# Program License: Amazon License
# Python Class License: Apache 2.0
#
# Purpose: This program (taskcat) is a caloudformation testing tool
# Tests can defined in a configuration yaml (config.yml)
# @TODO
        # system level configuration (sys will override repo configs)
        # if os.path.isfile(sys_yml):
        # taskcat.load_sysymal(sys_yml)

from taskcat import TaskCat
import yaml

def main():
    tcat_instance = TaskCat()
    tcat_instance.welcome('taskcat')
    # Initalize cli interface
    # @TODO Add RestFull Interface
    args = tcat_instance.interface
    
    # Get configuration from command line arg (-c)
    tcat_instance.set_config(args.config_yml)
    # tcat_instance.set_config('ci/config.yml')
    # Get API Handle - Try all know auth
    tcat_instance.aws_api_init(args)
    # Enable verbose output by default (DEBUG ON)
    tcat_instance.verbose = True
# --Begin
# Check for valid ymal and required keys in config
    if args.config_yml is not None:
        print "[TASKCAT] : Reading Configuration form: \t [%s]" % args.config_yml


        test_list = tcat_instance.validate_yaml(args.config_yml)

# Load ymal into local taskcat config
        with open(tcat_instance.get_config(), 'r') as cfg:
            taskcat_cfg = yaml.safe_load(cfg.read())
        cfg.close()

        tcat_instance.stage_in_s3(taskcat_cfg)
        tcat_instance.validate_template(taskcat_cfg, test_list)
        tcat_instance.validate_parameters(taskcat_cfg, test_list)
        stackinfo = tcat_instance.stackcreate(taskcat_cfg, test_list, 'tonyv')
        tcat_instance.get_stackstatus(stackinfo , 5)
        tcat_instance.cleanup(stackinfo , 5)

# --End

main()
