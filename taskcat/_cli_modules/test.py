# pylint: disable=duplicate-code
# noqa: B950,F841
import logging
from pathlib import Path
from typing import List as ListType

import boto3

from taskcat._cfn._log_stack_events import _CfnLogTools
from taskcat._cfn.threaded import Stacker
from taskcat._cfn_lint import Lint as TaskCatLint
from taskcat._client_factory import Boto3Cache
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
    @staticmethod  # noqa: C901
    def run(  # noqa: C901
        input_file: str = "./.taskcat.yml",
        project_root: str = "./",
        no_delete: bool = False,
        lint_disable: bool = False,
        enable_sig_v2: bool = False,
        keep_failed: bool = False,
    ):
        """tests whether CloudFormation templates are able to successfully launch

        :param input_file: path to either a taskat project config file or a
        CloudFormation template
        :param project_root_path: root path of the project relative to input_file
        :param no_delete: don't delete stacks after test is complete
        :param lint_disable: disable cfn-lint checks
        :param enable_sig_v2: enable legacy sigv2 requests for auto-created buckets
        :param keep_failed: do not delete failed stacks
        """
        project_root_path: Path = Path(project_root).expanduser().resolve()
        input_file_path: Path = project_root_path / input_file
        config = Config.create(
            project_root=project_root_path,
            project_config_path=input_file_path
            # TODO: detect if input file is taskcat config or CloudFormation template
        )

        if enable_sig_v2:
            config = Config.create(
                project_root=project_root_path,
                project_config_path=input_file_path,
                args={"project": {"s3_enable_sig_v2": enable_sig_v2}},
            )

        boto3_cache = Boto3Cache()
        templates = config.get_templates(project_root_path)
        # 1. lint
        if not lint_disable:
            lint = TaskCatLint(config, templates)
            errors = lint.lints[1]
            lint.output_results()
            if errors or not lint.passed:
                raise TaskCatException("Lint failed with errors")
        # 2. build lambdas
        LambdaBuild(config, project_root_path)
        # 3. s3 sync
        buckets = config.get_buckets(boto3_cache)
        stage_in_s3(buckets, config.config.project.name, project_root_path)
        # 4. launch stacks
        regions = config.get_regions(boto3_cache)
        parameters = config.get_rendered_parameters(buckets, regions, templates)
        tests = config.get_tests(
            project_root_path, templates, regions, buckets, parameters
        )
        test_definition = Stacker(
            config.config.project.name,
            tests,
            shorten_stack_name=config.config.project.shorten_stack_name,
        )
        test_definition.create_stacks()
        terminal_printer = TerminalPrinter()
        # 5. wait for completion
        terminal_printer.report_test_progress(stacker=test_definition)
        status = test_definition.status()
        # 6. create report
        report_path = Path("./taskcat_outputs/").resolve()
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
                terminal_printer.report_test_progress(stacker=test_definition)
        else:
            test_definition.delete_stacks()
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
