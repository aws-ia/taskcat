# pylint: disable=duplicate-code
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3

from taskcat._cfn.stack import Stack
from taskcat._cfn.threaded import Stacker
from taskcat._client_factory import Boto3Cache
from taskcat.regions_to_partitions import REGIONS

LOG = logging.getLogger(__name__)


class Delete:
    """[ALPHA] Deletes an installed project in an AWS account/region"""

    # pylint: disable=too-many-locals
    def __init__(
        self,
        project: str,
        aws_profile: str = "default",
        region="ALL",
        no_verify: bool = False,
        stack_type: str = "ALL",
    ):
        """
        :param project: installed project to delete, can be an install name, uuid, or project name
        :param aws_profile: aws profile to use for deletion
        :param region: region(s) to delete from, by default, will delete all applicable\
            stacks, supply a csv "us-east-1,us-west-1" to override this default
        :param no_verify: ignore region verification, delete will not error if an invalid\
            region is detected
        :param stack_type: type of stacks to delete, allowable options are ["project","test","ALL"]
        """
        boto3_cache = Boto3Cache()
        if region == "default":
            regions = boto3_cache.get_default_region(aws_profile)
        elif region == "ALL":
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
        elif isinstance(region, str):
            regions = (
                self._validate_regions(region) if not no_verify else region.split(",")
            )
        stacks = Stacker.list_stacks([aws_profile], regions)
        jobs = []
        for stack in stacks:
            name = stack.get("taskcat-installer", stack["taskcat-project-name"])
            job = {
                "name": name,
                "project_name": stack["taskcat-project-name"],
                "test_name": stack["taskcat-test-name"],
                "taskcat_id": stack["taskcat-id"].hex,
                "region": stack["region"],
                "stack_id": stack["stack-id"],
            }
            if stack_type in ["project", "ALL"] and project in [
                job["name"],
                job["taskcat_id"],
                "ALL",
            ]:
                jobs.append(job)
            if stack_type in ["test", "ALL"] and project in [
                job["project_name"],
                "ALL",
            ]:
                jobs.append(job)
        with ThreadPoolExecutor() as executor:
            stack_futures = {
                executor.submit(
                    self._delete_stack,
                    boto3_cache=boto3_cache,
                    job=job,
                    aws_profile=aws_profile,
                ): [job["name"], job["region"]]
                for job in jobs
            }

            for stack_future in as_completed(stack_futures):
                name_and_region = stack_futures[stack_future]
                try:
                    stack_future.result()
                # pylint: disable=broad-except
                except Exception:
                    LOG.error(f"{name_and_region[0]} failed in {name_and_region[1]}")
                else:
                    LOG.info(f"{name_and_region[0]} deleted in {name_and_region[1]}")

    @staticmethod
    def _delete_stack(boto3_cache, job, aws_profile):
        client = boto3_cache.client(
            "cloudformation", profile=aws_profile, region=job["region"]
        )
        Stack.delete(client=client, stack_id=job["stack_id"])

    # Checks if all regions are valid
    @staticmethod
    def _validate_regions(region_string):
        regions = region_string.split(",")
        for region in regions:
            if region not in REGIONS:
                LOG.error(f"Bad region detected: {region}")
                sys.exit(1)
        return regions
