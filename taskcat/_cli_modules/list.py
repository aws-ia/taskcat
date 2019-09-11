import logging
import boto3

from taskcat._cfn.threaded import Stacker

LOG = logging.getLogger(__name__)


class List:
    """lists taskcat jobs with active stacks"""

    def __init__(self, profiles: str = "default", regions="ALL"):
        """
        :param profiles: comma separated list of aws profiles to search
        :param regions: comma separated list of regions to search, default is to check
        all commercial regions
        """
        profiles = profiles.split(",")
        if regions == "ALL":
            region_set = set()
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
        jobs = {}
        for stack in stacks:
            if stack["taskcat-id"].hex not in jobs:
                jobs[stack["taskcat-id"].hex] = {
                    "name": stack["taskcat-project-name"],
                    "active_stacks": 1,
                }
            else:
                jobs[stack["taskcat-id"].hex]["active_stacks"] += 1
        longest_name = sorted([len(v["name"]) for _, v in jobs.items()])[-1]

        def spaces(number):
            ret = ""
            for s in range(number):
                ret += " "
            return ret

        def pad(string, length):
            while len(string) < length:
                string += " "
            return string

        header = f"NAME{spaces(longest_name)}ID{spaces(34)}NUMBER_OF_STACKS"
        LOG.error(header, extra={"nametag": ""})
        column = "{}    {}    {}"
        for job_id, job in jobs.items():
            LOG.error(
                column.format(
                    pad(job["name"], longest_name), job_id, job["active_stacks"]
                ),
                extra={"nametag": ""},
            )
