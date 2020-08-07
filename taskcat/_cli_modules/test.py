# pylint: disable=duplicate-code
# noqa: B950,F841
import logging
from pathlib import Path
from typing import Any, Dict, List as ListType

import boto3
import yaml

from taskcat._cfn._log_stack_events import _CfnLogTools
from taskcat._cfn.threaded import Stacker
from taskcat._cfn_lint import Lint as TaskCatLint
from taskcat._cli_core import GLOBAL_ARGS
from taskcat._client_factory import Boto3Cache
from taskcat._common_utils import determine_profile_for_region
from taskcat._config import Config
from taskcat._generate_reports import ReportBuilder
from taskcat._lambda_build import LambdaBuild
from taskcat._s3_stage import stage_in_s3
from taskcat._tui import TerminalPrinter
from taskcat.exceptions import TaskCatException

from .delete import Delete
from .list import List

LOG = logging.getLogger(__name__)


class Test:
    """
    Performs functional tests on CloudFormation templates.
    """

    # pylint: disable=too-many-locals
    @staticmethod
    def retry(
        region: str,
        stack_name: str,
        resource_name: str,
        config_file: str = "./.taskcat.yml",
        project_root: str = "./",
        no_delete: bool = False,
        keep_failed: bool = False,
        minimal_output: bool = False,
        dont_wait_for_delete: bool = False,
    ):
        """[ALPHA] re-launches a child stack using the same parameters as previous
        launch

        :param region: region stack is in
        :param stack_name: name of parent stack
        :param resource_name: logical id of child stack that will be re-launched
        :param config_file: path to either a taskat project config file or a
        CloudFormation template
        :param project_root: root path of the project relative to input_file
        :param no_delete: don't delete stacks after test is complete
        :param keep_failed: do not delete failed stacks
        :param minimal_output: Reduces output during test runs
        :param dont_wait_for_delete: Exits immediately after calling stack_delete
        """
        LOG.warning("test retry is in alpha feature, use with caution")
        project_root_path: Path = Path(project_root).expanduser().resolve()
        input_file_path: Path = project_root_path / config_file
        config = Config.create(
            project_root=project_root_path, project_config_path=input_file_path
        )
        profile = determine_profile_for_region(config.config.general.auth, region)
        cfn = boto3.Session(profile_name=profile).client(
            "cloudformation", region_name=region
        )
        events = cfn.describe_stack_events(StackName=stack_name)["StackEvents"]
        resource = [i for i in events if i["LogicalResourceId"] == resource_name][0]
        properties = yaml.safe_load(resource["ResourceProperties"])

        with open(str(input_file_path), "r") as filepointer:
            config_yaml = yaml.safe_load(filepointer)

        config_yaml["project"]["regions"] = [region]
        config_yaml["project"]["parameters"] = properties["Parameters"]
        config_yaml["project"]["template"] = "/".join(
            properties["TemplateURL"].split("/")[4:]
        )
        config_yaml["tests"] = {"default": {}}

        with open("/tmp/.taskcat.yml.temp", "w") as filepointer:  # nosec
            yaml.safe_dump(config_yaml, filepointer)

        if resource["PhysicalResourceId"]:
            cfn.delete_stack(StackName=resource["PhysicalResourceId"])
            LOG.info("waiting for old stack to delete...")
            cfn.get_waiter("stack_delete_complete").wait(
                StackName=resource["PhysicalResourceId"]
            )

        Test.run(
            input_file="/tmp/.taskcat.yml.temp",  # nosec
            project_root=project_root,
            lint_disable=True,
            no_delete=no_delete,
            keep_failed=keep_failed,
            minimal_output=minimal_output,
            dont_wait_for_delete=dont_wait_for_delete,
        )

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    @staticmethod  # noqa: C901
    # pylint: disable=too-many-arguments
    def run(  # noqa: C901
        test_names: str = "ALL",
        regions: str = "ALL",
        input_file: str = "./.taskcat.yml",
        project_root: str = "./",
        no_delete: bool = False,
        lint_disable: bool = False,
        enable_sig_v2: bool = False,
        keep_failed: bool = False,
        output_directory: str = "./taskcat_outputs",
        minimal_output: bool = False,
        dont_wait_for_delete: bool = False,
        skip_upload: bool = False,
    ):
        """tests whether CloudFormation templates are able to successfully launch

        :param test_names: comma separated list of tests to run
        :param regions: comma separated list of regions to test in
        :param input_file: path to either a taskat project config file or a
        CloudFormation template
        :param project_root: root path of the project relative to input_file
        :param no_delete: don't delete stacks after test is complete
        :param lint_disable: disable cfn-lint checks
        :param enable_sig_v2: enable legacy sigv2 requests for auto-created buckets
        :param keep_failed: do not delete failed stacks
        :param output_directory: Where to store generated logfiles
        :param minimal_output: Reduces output during test runs
        :param dont_wait_for_delete: Exits immediately after calling stack_delete
        """
        project_root_path: Path = Path(project_root).expanduser().resolve()
        input_file_path: Path = project_root_path / input_file
        # pylint: disable=too-many-arguments
        args = _build_args(enable_sig_v2, regions, GLOBAL_ARGS.profile)
        config = Config.create(
            project_root=project_root_path,
            project_config_path=input_file_path,
            args=args
            # TODO: detect if input file is taskcat config or CloudFormation template
        )
        _trim_regions(regions, config)
        _trim_tests(test_names, config)
        boto3_cache = Boto3Cache()
        templates = config.get_templates()
        if skip_upload and not config.config.project.s3_bucket:
            raise TaskCatException(
                "cannot skip_buckets without specifying s3_bucket in config"
            )
        buckets = config.get_buckets(boto3_cache)
        if not skip_upload:
            # 1. lint
            if not lint_disable:
                lint = TaskCatLint(config, templates)
                errors = lint.lints[1]
                lint.output_results()
                if errors or not lint.passed:
                    raise TaskCatException("Lint failed with errors")
            # 2. build lambdas
            if config.config.project.package_lambda:
                LambdaBuild(config, project_root_path)
            # 3. s3 sync
            stage_in_s3(buckets, config.config.project.name, config.project_root)
        # 4. launch stacks
        regions = config.get_regions(boto3_cache)
        parameters = config.get_rendered_parameters(buckets, regions, templates)
        tests = config.get_tests(templates, regions, buckets, parameters)
        test_definition = Stacker(
            config.config.project.name,
            tests,
            shorten_stack_name=config.config.project.shorten_stack_name,
        )
        test_definition.create_stacks()
        terminal_printer = TerminalPrinter(minimalist=minimal_output)
        # 5. wait for completion
        terminal_printer.report_test_progress(stacker=test_definition)
        status = test_definition.status()
        # 6. create report
        report_path = Path(output_directory).resolve()
        report_path.mkdir(exist_ok=True)
        cfn_logs = _CfnLogTools()
        cfn_logs.createcfnlogs(test_definition, report_path)
        ReportBuilder(test_definition, report_path / "index.html").generate_report()
        # 7. delete stacks
        if no_delete:
            LOG.info("Skipping delete due to cli argument")
        elif keep_failed:
            if len(status["COMPLETE"]) > 0:
                LOG.info("deleting successful stacks")
                test_definition.delete_stacks({"status": "CREATE_COMPLETE"})
                if not dont_wait_for_delete:
                    terminal_printer.report_test_progress(stacker=test_definition)
        else:
            test_definition.delete_stacks()
            if not dont_wait_for_delete:
                terminal_printer.report_test_progress(stacker=test_definition)
        # TODO: summarise stack statusses (did they complete/delete ok) and print any
        #  error events
        # 8. delete buckets

        if not no_delete or (keep_failed is True and len(status["FAILED"]) == 0):
            deleted: ListType[str] = []
            for test in buckets.values():
                for bucket in test.values():
                    if (bucket.name not in deleted) and not bucket.regional_buckets:
                        bucket.delete(delete_objects=True)
                        deleted.append(bucket.name)
        # 9. raise if something failed
        if len(status["FAILED"]) > 0:
            raise TaskCatException(
                f'One or more stacks failed tests: {status["FAILED"]}'
            )

    def resume(self, run_id):  # pylint: disable=no-self-use
        """resumes a monitoring of a previously started test run"""
        # do some stuff
        raise NotImplementedError()

    @staticmethod
    def list(profiles: str = "default", regions="ALL", _stack_type="package"):
        """
        :param profiles: comma separated list of aws profiles to search
        :param regions: comma separated list of regions to search, default is to check
        all commercial regions
        """
        List(profiles=profiles, regions=regions, _stack_type="test")

    @staticmethod
    def clean(project: str, aws_profile: str = "default", region="ALL"):
        """
        :param project: project to delete, can be an name or uuid, or ALL to clean all
        tests
        :param aws_profile: aws profile to use for deletion
        :param region: region to delete from, default will scan all regions
        """
        if region == "ALL":
            region_set: set = set()
            region_set = region_set.union(
                # pylint: disable=duplicate-code
                set(
                    boto3.Session(profile_name=aws_profile).get_available_regions(
                        "cloudformation"
                    )
                )
            )
            regions = list(region_set)
        else:
            regions = [region]
        Delete(
            package=project, aws_profile=aws_profile, region=regions, _stack_type="test"
        )


def _trim_regions(regions, config):
    if regions != "ALL":
        for test in config.config.tests.values():
            to_pop = []
            idx = 0
            if test.regions:
                for _ in test.regions:
                    if test.regions[idx] not in regions.split(","):
                        to_pop.append(idx)
                    idx += 1
                to_pop.reverse()
                for idx in to_pop:
                    test.regions.pop(idx)


def _trim_tests(test_names, config):
    if test_names != "ALL":
        for test in list(config.config.tests):
            if test not in test_names.split(","):
                del config.config.tests[test]


def _build_args(enable_sig_v2, regions, default_profile):
    args: Dict[str, Any] = {}
    if enable_sig_v2:
        args["project"] = {"s3_enable_sig_v2": enable_sig_v2}
    if regions != "ALL":
        if "project" not in args:
            args["project"] = {}
        args["project"]["regions"] = regions.split(",")
    if default_profile:
        _auth_dict = {"default": default_profile}
        if not args.get("project"):
            args["project"] = {"auth": _auth_dict}
        else:
            args["project"]["auth"] = _auth_dict
    return args
