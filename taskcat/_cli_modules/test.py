# pylint: disable=duplicate-code
# noqa: B950,F841
import inspect
import logging
import os
import sys
import tempfile
from pathlib import Path

import boto3
import yaml

from taskcat._common_utils import determine_profile_for_region
from taskcat._config import Config
from taskcat._tui import TerminalPrinter
from taskcat.testing import CFNTest

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

        with open(str(input_file_path), "r", encoding="utf-8") as filepointer:
            config_yaml = yaml.safe_load(filepointer)

        config_yaml["project"]["regions"] = [region]
        config_yaml["project"]["parameters"] = properties["Parameters"]
        config_yaml["project"]["template"] = "/".join(
            properties["TemplateURL"].split("/")[4:]
        )
        config_yaml["tests"] = {"default": {}}

        tmpdir = tempfile.mkdtemp()
        name = ".taskcat.yml.temp"
        umask = os.umask(0o77)
        file_path = os.path.join(tmpdir, name)
        try:
            with open(file_path, "w", encoding="utf-8") as filepointer:  # nosec
                yaml.safe_dump(config_yaml, filepointer)
            if resource["PhysicalResourceId"]:
                cfn.delete_stack(StackName=resource["PhysicalResourceId"])
                LOG.info("waiting for old stack to delete...")
                cfn.get_waiter("stack_delete_complete").wait(
                    StackName=resource["PhysicalResourceId"]
                )

            Test.run(
                input_file=file_path,  # nosec
                project_root=project_root,
                lint_disable=True,
                no_delete=no_delete,
                keep_failed=keep_failed,
                minimal_output=minimal_output,
                dont_wait_for_delete=dont_wait_for_delete,
            )
        except IOError:
            LOG.error("IOError when retrying Test Run")
            sys.exit(1)
        else:
            os.remove(file_path)
        finally:
            os.umask(umask)
            os.rmdir(tmpdir)

    @staticmethod
    # pylint: disable=too-many-arguments,W0613,line-too-long
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
        _extra_tags: List = None,
    ):
        """tests whether CloudFormation templates are able to successfully launch
        :param test_names: comma separated list of tests to run
        :param regions: comma separated list of regions to test in
        :param input_file: path to either a taskat project config file or a CloudFormation template
        :param project_root: root path of the project relative to input_file
        :param no_delete: don't delete stacks after test is complete
        :param lint_disable: disable cfn-lint checks
        :param enable_sig_v2: enable legacy sigv2 requests for auto-created buckets
        :param keep_failed: do not delete failed stacks
        :param output_directory: Where to store generated logfiles
        :param minimal_output: Reduces output during test runs
        :param dont_wait_for_delete: Exits immediately after calling stack_delete
        :param skip_upload: Use templates in an existing cloudformation bucket.
        """  # noqa: B950

        test = CFNTest.from_file(
            project_root=project_root,
            input_file=input_file,
            regions=regions,
            enable_sig_v2=enable_sig_v2,
        )

        # This code is temporary and should be removed once its easier
        # to create a config object
        frame = inspect.currentframe()

        if frame is not None:
            args, _, _, values = inspect.getargvalues(frame)

            for i in args:
                if hasattr(test, i):
                    setattr(test, i, values[i])

        terminal_printer = TerminalPrinter(minimalist=minimal_output)

        test.printer = terminal_printer

        # Runs here
        with test:
            test.report(output_directory)

    def resume(self, run_id):
        """resumes a monitoring of a previously started test run"""
        # do some stuff
        raise NotImplementedError()

    @staticmethod
    def list(profiles: str = "default", regions="ALL"):
        """
        :param profiles: comma separated list of aws profiles to search
        :param regions: comma separated list of regions to search, default is to check
        all commercial regions
        """
        List(profiles=profiles, regions=regions, stack_type="test")

    @staticmethod
    def clean(project: str, aws_profile: str = "default", region="ALL"):
        """
        :param project: project to delete, can be an name or uuid, or ALL to clean all
        tests
        :param aws_profile: aws profile to use for deletion
        :param region: region to delete from, default will scan all regions
        """
        Delete(
            project=project, aws_profile=aws_profile, region=region, stack_type="test"
        )
