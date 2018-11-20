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
import os
import sys
import traceback
import argparse
import pyfiglet
import requests
import logging
from argparse import RawTextHelpFormatter
from pkg_resources import get_distribution
from taskcat.common_utils import exit0, exit1
from taskcat.lambda_build import LambdaBuild
from taskcat.cfn_lint import Lint
from taskcat.logger import init_taskcat_cli_logger, PrintMsg
from taskcat.exceptions import TaskCatException

log = logging.getLogger(__name__)


def main():
    try:
        args = _parse_args()
        log = init_taskcat_cli_logger(loglevel=args.verbosity)
        welcome('taskcat')
        tcat_instance = taskcat.TaskCat(args)
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

            # If taskcat is being executed from the project root folder, cd out and update config path
            try:
                if os.path.basename(os.path.abspath(os.path.curdir)) == taskcat_cfg['global']['qsname']:
                    config_path = tcat_instance.get_config()[2:] if tcat_instance.get_config().startswith(
                        "./") else tcat_instance.get_config()
                    os.chdir(os.path.abspath("../"))
                    tcat_instance.set_config("%s/%s" % (taskcat_cfg['global']['qsname'], config_path))
            except Exception as e:
                log.error(str(e))
            project_path = '/'.join(tcat_instance.get_config().split('/')[0:-3])
            project_name = '/'.join(tcat_instance.get_config().split('/')[-3:-2])
            if "package-lambda" not in taskcat_cfg['global']:
                taskcat_cfg['global']["package-lambda"] = False
            if tcat_instance.lambda_build_only and not taskcat_cfg['global']["package-lambda"]:
                exit1("Lambda build not enabled for project. Add package-lambda: true to config.yaml global section")
            elif taskcat_cfg['global']["package-lambda"]:
                try:
                    lambda_path = os.path.abspath(project_path) + "/" + project_name + "/functions/source"
                    if os.path.isdir(lambda_path):
                        LambdaBuild(lambda_path)
                except Exception as e:
                    log.error("Zipping lambda source failed: %s" % e)
                if tcat_instance.lambda_build_only:
                    exit0("Lambda source zipped successfully")
            try:
                if project_path:
                    os.chdir(os.path.abspath(project_path))
                Lint(config=tcat_instance.get_config(), path=project_name).output_results()
            except taskcat.exceptions.TaskCatException as e:
                log.error(str(e))
                exit1(str(e))
            except Exception as e:
                log.error("Linting failed: %s" % e)
                traceback.print_exc()
            if args.lint:
                exit0("Linting completed")
            tcat_instance.stage_in_s3(taskcat_cfg)
            tcat_instance.validate_template(taskcat_cfg, test_list)
            tcat_instance.validate_parameters(taskcat_cfg, test_list)
            # instance.stackcreate returns testdata object
            testdata = tcat_instance.stackcreate(taskcat_cfg, test_list, args.stack_prefix)
            tcat_instance.get_stackstatus(testdata, 5)
            tcat_instance.createreport(testdata, 'index.html')
            tcat_instance.cleanup(testdata, 5)
    except taskcat.TaskCatException as e:
        log.error(str(e))
        exit1(str(e))


def _parse_args():
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
        '-N',
        '--no_cleanup_failed',
        action='store_true',
        help="Sets cleaup to false if the stack launch fails (Does not teardown stacks if it experiences a failure)"
    )
    parser.add_argument(
        '-p',
        '--public_s3_bucket',
        action='store_true',
        help="Sets public_s3_bucket to True. (Accesses objects via public HTTP, not S3 API calls)")
    parser.add_argument(
        '-v',
        '--verbosity',
        type=str,
        default="warn",
        help="Sets output verbosity to appropriate level, valid values are debug, info, warning, error")
    parser.add_argument(
        '-t',
        '--tag',
        action=AppendTag,
        help="add tag to cloudformation stack, must be in the format TagKey=TagValue, multiple -t can be specified")
    parser.add_argument(
        '-s',
        '--stack-prefix',
        type=str,
        default="tag",
        help="set prefix for cloudformation stack name. only accepts lowercase letters, numbers and '-'")
    parser.add_argument(
        '-l',
        '--lint',
        action='store_true',
        help="lint the templates and exit")
    parser.add_argument(
        '-V',
        '--version',
        action='store_true',
        help="Prints Version")
    parser.add_argument(
        '-u',
        '--upload-only',
        action='store_true',
        help="Sync local files with s3 and exit")
    parser.add_argument(
        '-b',
        '--lambda-build-only',
        action='store_true',
        help="create lambda zips and exit")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        welcome()
        print(parser.print_help())
        exit0()

    if args.version:
        print(get_installed_version())
        exit0()

    if args.boto_profile is not None:
        if args.aws_access_key is not None or args.aws_secret_key is not None:
            print(parser.print_help())
            raise TaskCatException("Cannot use boto profile -P (--boto_profile) with --aws_access_key or --aws_secret_key")

    if not args.config_yml:
        parser.error("-c (--config_yml) not passed (Config File Required!)")
        print(parser.print_help())
        raise TaskCatException("-c (--config_yml) not passed (Config File Required!)")

    if args.no_cleanup_failed:
        if args.no_cleanup:
            parser.error("Cannot use -n (--no_cleanup) with -N (--no_cleanup_failed)")
            print(parser.print_help())
            raise TaskCatException("Cannot use -n (--no_cleanup) with -N (--no_cleanup_failed)")

    return args


class AppendTag(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if len(values.split('=')) != 2:
            raise TaskCatException("tags must be in the format TagKey=TagValue")
        n, v = values.split('=')
        try:
            getattr(namespace, 'tags')
        except AttributeError:
            setattr(namespace, 'tags', [])
        namespace.tags.append({"Key": n, "Value": v})


def checkforupdate():

    def _print_upgrade_msg(newversion):
        log.info("version %s\n" % version, extra={"nametag": ""})
        log.warning("A newer version of {} is available ({})".format('taskcat', newversion))
        log.info('To upgrade pip version    {}[ pip install --upgrade taskcat]{}'.format(
                    PrintMsg.highlight, PrintMsg.rst_color))
        log.info('To upgrade docker version {}[ docker pull taskcat/taskcat ]{}\n'.format(
                    PrintMsg.highlight, PrintMsg.rst_color))

    version = get_installed_version()
    if version != "[local source] no pip module installed":
        if 'dev' not in version:
            current_version = get_pip_version(
                'https://pypi.org/pypi/taskcat/json')
            if version in current_version:
                log.info("version %s" % version, extra={"nametag": ''})
            else:
                _print_upgrade_msg(current_version)
    else:
        log.info("Using local source (development mode)\n")


def welcome(prog_name='taskcat'):
    banner = pyfiglet.Figlet(font='standard')
    banner = banner
    log.info("{0}".format(banner.renderText(prog_name), '\n'), extra={"nametag": ""})
    try:
        checkforupdate()
    except TaskCatException:
        raise
    except Exception:
        log.debug("Traceback", exc_info=True)
        log.warning("Unable to get version info!!, continuing")
        pass


def get_pip_version(url):
    '''
    Given the url to PypI package info url returns the current live version
    '''
    return requests.get(url).json()["info"]["version"]


def get_installed_version():
    try:
        return get_distribution('taskcat').version.replace('.0', '.')
    except Exception:
        return "[local source] no pip module installed"
