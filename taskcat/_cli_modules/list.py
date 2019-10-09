# pylint: disable=duplicate-code
import logging
from typing import List as ListType, Union

import boto3

from taskcat._cfn.threaded import Stacker

LOG = logging.getLogger(__name__)


class List:
    """[ALPHA] lists taskcat jobs with active stacks"""

    # pylint: disable=too-many-locals
    def __init__(  # noqa: C901
        self,
        profiles: Union[str, ListType[str]] = "default",
        regions="ALL",
        _stack_type="package",
    ):
        """
        :param profiles: comma separated list of aws profiles to search
        :param regions: comma separated list of regions to search, default is to check
        all commercial regions
        """
        LOG.warning("list is in alpha feature, use with caution")
        if isinstance(profiles, str):
            profiles = profiles.split(",")
        if regions == "ALL":
            region_set: set = set()
            for profile in profiles:
                region_set = region_set.union(
                    set(
                        boto3.Session(profile_name=profile).get_available_regions(
                            "cloudformation"
                        )
                    )
                )
            regions = list(region_set)
        else:
            regions = regions.split(",")
        stacks = Stacker.list_stacks(profiles, regions)
        jobs: dict = {}
        for stack in stacks:
            if stack["taskcat-id"].hex not in jobs:
                name = stack.get("taskcat-installer")
                if _stack_type == "test" and not name:
                    name = stack["taskcat-project-name"]
                    jobs[stack["taskcat-id"].hex] = {
                        "name": name,
                        "project_name": stack["taskcat-project-name"],
                        "active_stacks": 1,
                        "region": stack["region"],
                    }
                elif name and _stack_type == "package":
                    jobs[stack["taskcat-id"].hex] = {
                        "name": name,
                        "project_name": stack["taskcat-project-name"],
                        "active_stacks": 1,
                        "region": stack["region"],
                    }
            else:
                jobs[stack["taskcat-id"].hex]["active_stacks"] += 1

        def longest(things: list):
            lengths = [len(thing) for thing in things]
            return sorted(lengths)[-1] if lengths else 0

        def spaces(number):
            ret = ""
            for _ in range(number):
                ret += " "
            return ret

        def pad(string, length):
            while len(string) < length:
                string += " "
            return string

        longest_name = longest([v["name"] for _, v in jobs.items()])
        longest_project_name = longest([v["project_name"] for _, v in jobs.items()])
        if not jobs:
            LOG.info("no stacks found")
            return
        header = (
            f"NAME{spaces(longest_name)}PROJECT{spaces(longest_project_name)}"
            f"ID{spaces(34)}REGION"
        )
        LOG.error(header, extra={"nametag": ""})
        column = "{}    {}       {}    {}"
        for job_id, job in jobs.items():
            LOG.error(
                column.format(
                    pad(job["name"], longest_name),
                    pad(job["project_name"], longest_project_name),
                    job_id,
                    job["region"],
                ),
                extra={"nametag": ""},
            )
