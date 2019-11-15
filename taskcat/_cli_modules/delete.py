# pylint: disable=duplicate-code
import logging

from taskcat._cfn.stack import Stack
from taskcat._cfn.threaded import Stacker
from taskcat._client_factory import Boto3Cache

LOG = logging.getLogger(__name__)


class Delete:
    """[ALPHA] Deletes an installed package in an AWS account/region"""

    def __init__(
        self,
        package: str,
        aws_profile: str = "default",
        region="default",
        _stack_type="package",
    ):
        """
        :param package: installed package to delete, can be an install name or uuid
        :param aws_profile: aws profile to use for deletion
        :param region: region to delete from, default will use aws cli configured
        default
        """
        LOG.warning("delete is in alpha feature, use with caution")
        boto3_cache = Boto3Cache()
        if region == "default":
            region = boto3_cache.get_default_region(aws_profile)
        if isinstance(region, str):
            region = [region]
        stacks = Stacker.list_stacks([aws_profile], region)
        jobs = []
        for stack in stacks:
            name = stack.get("taskcat-installer", stack["taskcat-project-name"])
            job = {
                "name": name,
                "project_name": stack["taskcat-project-name"],
                "test_name": stack["taskcat-test-name"],
                "taskcat_id": stack["taskcat-id"].hex,
                "region": stack["region"],
                "type": "package" if stack.get("taskcat-installer") else "test",
                "stack_id": stack["stack-id"],
            }
            if _stack_type == job["type"]:
                if package in [job["name"], job["taskcat_id"], "ALL"]:
                    jobs.append(job)
        # TODO: concurrency and wait for complete
        for job in jobs:
            client = boto3_cache.client(
                "cloudformation", profile=aws_profile, region=job["region"]
            )
            Stack.delete(client=client, stack_id=job["stack_id"])
