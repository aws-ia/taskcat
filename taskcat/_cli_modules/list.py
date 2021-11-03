# pylint: disable=duplicate-code
import logging
from typing import List as ListType, Union

import boto3

from taskcat._cfn.threaded import Stacker

LOG = logging.getLogger(__name__)


class List:
    """[ALPHA] lists taskcat jobs with active stacks"""

    # pylint: disable=too-many-locals,too-many-branches
    def __init__(  # noqa: C901
        self,
        profiles: Union[str, ListType[str]] = "default",
        regions="ALL",
        stack_type="ALL",
    ):
        """
        :param profiles: comma separated list of aws profiles to search
        :param regions: comma separated list of regions to search, default is to check \
            all commercial regions
        :param stack_type: type of stacks to check, options are 'test', 'project', or 'ALL'. \
            default is 'ALL'
        """
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
            stack_key = stack["taskcat-id"].hex + "-" + stack["region"]
            if stack_key not in jobs:
                name = stack.get("taskcat-installer")
                if stack_type == "ALL":
                    if not name:
                        name = stack["taskcat-project-name"]
                    jobs[stack_key] = {
                        "name": name,
                        "id": stack["taskcat-id"].hex,
                        "project_name": stack["taskcat-project-name"],
                        "active_stacks": 1,
                        "region": stack["region"],
                    }
                elif stack_type == "test" and not name:
                    name = stack["taskcat-project-name"]
                    jobs[stack_key] = {
                        "name": name,
                        "id": stack["taskcat-id"].hex,
                        "project_name": stack["taskcat-project-name"],
                        "active_stacks": 1,
                        "region": stack["region"],
                    }
                elif name and stack_type == "project":
                    jobs[stack_key] = {
                        "name": name,
                        "id": stack["taskcat-id"].hex,
                        "project_name": stack["taskcat-project-name"],
                        "active_stacks": 1,
                        "region": stack["region"],
                    }
            else:
                jobs[stack_key]["active_stacks"] += 1

        longest_name = List._longest([v["name"] for _, v in jobs.items()])
        longest_project_name = List._longest(
            [v["project_name"] for _, v in jobs.items()]
        )
        if not jobs:
            LOG.info("no stacks found")
            return
        if stack_type != "test":
            header = (
                f"NAME{List._spaces(longest_name)}PROJECT{List._spaces(longest_project_name)}"
                f"ID{List._spaces(34)}REGION"
            )
            column = "{}    {}       {}    {}"
        else:
            header = f"NAME{List._spaces(longest_name)}ID{List._spaces(34)}REGION"
            column = "{}    {}    {}"
        LOG.error(header, extra={"nametag": ""})
        for job in jobs.values():
            args = [
                List._pad(job["name"], longest_name),
                List._pad(job["project_name"], longest_project_name),
                job["id"],
                job["region"],
            ]
            if stack_type == "test":
                args = [List._pad(job["name"], longest_name), job["id"], job["region"]]
            LOG.error(column.format(*args), extra={"nametag": ""})

    @staticmethod
    def _longest(things: list):
        lengths = [len(thing) for thing in things]
        return sorted(lengths)[-1] if lengths else 0

    @staticmethod
    def _spaces(number):
        ret = ""
        for _ in range(number):
            ret += " "
        return ret

    @staticmethod
    def _pad(string, length):
        while len(string) < length:
            string += " "
        return string
