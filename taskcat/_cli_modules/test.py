# pylint: disable=duplicate-code
# noqa: B950,F841
import logging
from pathlib import Path

import boto3
import yaml

from taskcat._common_utils import determine_profile_for_region
from taskcat._config import Config
from taskcat.testing.manager import TestManager

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
        # Create a TestManager and start the Tests
        test_manager = TestManager.from_file(
            project_root, input_file, regions, enable_sig_v2
        )
        test_manager.minimal_output = minimal_output
        test_manager.start(test_names, regions, skip_upload, lint_disable)

        # Create Report
        test_manager.report(output_directory)

        test_manager.end(no_delete, keep_failed, dont_wait_for_delete)

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
