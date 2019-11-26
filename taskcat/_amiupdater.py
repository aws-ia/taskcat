import dataclasses
import datetime
import logging
import re
from dataclasses import dataclass, field
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool
from typing import Dict, List, Set

import pkg_resources
import yaml

from taskcat._cfn.template import Template as TCTemplate
from taskcat._common_utils import deep_get
from taskcat._dataclasses import RegionObj
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)

REGION_REGEX = re.compile(
    "((eu|ap|us|af|me|ca|cn|sa)-|(us-gov-))(north(east|west)?|south(east|west)?|central|east|west)-[0-9]",
    re.IGNORECASE)
class Config:
    raw_dict: dict = {"global": {"AMIs": {}}}
    codenames: Set[Dict[str, str]] = set()

    @classmethod
    def load(cls, fn, configtype=None):
        with open(fn, "r") as f:
            try:
                cls.raw_dict = yaml.safe_load(f)
            except yaml.YAMLError as e:
                LOG.error("[{}] - YAML Syntax Error!", fn)
                LOG.error("{}", e)
        try:
            for x in cls.raw_dict.get("global").get("AMIs").keys():
                cls.codenames.add(x)

        except Exception as e:
            LOG.error("{} config file [{}] is not structured properly!", configtype, fn)
            LOG.error("{}", e)
            raise AMIUpdaterFatalException

    @classmethod
    def update_filter(cls, dn):
        cls.raw_dict["global"]["AMIs"].update(dn)

    @classmethod
    def get_filter(cls, dn):
        x = deep_get(cls.raw_dict, f"global/AMIs/{dn}", {})
        return x


@dataclass
class EC2FilterValue:
    Name: str
    Values: List[str]


@dataclass
class APIResultsData(object):
    codename: str
    ami_id: str
    creation_date: int
    region: str
    custom_comparisons: bool = True

    def __lt__(self, other):
        # See Codenames.parse_api_results for notes on why this is here.
        if self.custom_comparisons:
            return self.creation_date < other.creation_date
        else:
            return object.__lt__(self, other)

    def __gt__(self, other):
        # See Codenames.parse_api_results for notes on why this is here.
        if self.custom_comparisons:
            return self.creation_date > other.creation_date
        else:
            return object.__gt__(self, other)


@dataclass
class RegionalCodename:
    region: str
    cn: str
    new_ami: str = ""
    filters: list = field(default_factory=list)
    _creation_dt: datetime.datetime = field(default_factory=datetime.datetime.now)

    def __hash__(self):
        return hash(self.region + self.cn + self.new_ami + str(self.filters))


class Template:
    def __init__(self, underlying: TCTemplate, regions_with_creds: List[str]):
        self.codenames: Set[Dict[str, str]] = set()
        self.mapping_path: str = "Mappings/AWSAMIRegionMap"
        self.metadata_path: str = "Metadata/AWSAMIRegionMap/Filters"
        self.region_codename_lineno: Dict[str, Dict[str, int]] = {}
        self.region_names: Set[str] = set()
        self.underlying: TCTemplate = underlying
        self._ls = self.underlying.linesplit
        _template_regions = deep_get(self.underlying.template, self.mapping_path, {})
        for region_name, region_data in _template_regions.items():
            if region_name == "AMI":
                continue
            self.region_names.add(region_name)
            for codename, cnvalue in region_data.items():
                key = f"{codename}/{region_name}"
                self.region_codename_lineno[key] = {
                    "line": line_no,
                    "old": cnvalue,
                }
        new_region_list = set()
        self.regions_without_creds: Set[str] = set()
        for region in self.region_names:
            if region not in regions_with_creds:
                self.regions_without_creds.add(region)
                continue
            new_region_list.add(region)
        self.region_names = new_region_list

    def set_codename_ami(self, cname, region, new_ami):
        if region not in self.region_names:
            return False
        key = f"{cname}/{region}"
        try:
            line_no = self.region_codename_lineno[key]["line"]
            old_ami = self.region_codename_lineno[key]["old"]
            if old_ami == new_ami:
                return False
        except KeyError:
            return False
        new_record = re.sub(old_ami, new_ami, self._ls[line_no])
        self._ls[line_no] = new_record
        return True

    def write(self):
        self.underlying.raw_template = "\n".join(self._ls)
        self.underlying.write()

class AMIUpdater:
    upstream_config_file = pkg_resources.resource_filename(
        "taskcat", "/cfg/amiupdater.cfg.yml"
    )
    upstream_config_file_url = (
        "https://raw.githubusercontent.com/aws-quickstart/"
        "taskcat/master/cfg/amiupdater.cfg.yml"
    )
    EXCLUDED_REGIONS = [
        "us-gov-east-1",
        "us-gov-west-1",
        "cn-northwest-1",
        "cn-north-1",
    ]

    def __init__(
        self,
        template_list,
        regions,
        boto3cache,
        user_config_file=None,
        use_upstream_mappings=True,
    ):
        if use_upstream_mappings:
            Config.load(self.upstream_config_file, configtype="Upstream")
        if user_config_file:
            Config.load(user_config_file, configtype="User")
        self.template_list = template_list
        self.boto3_cache = boto3cache
        self.regions = self._determine_testable_regions(regions)

    def _determine_testable_regions(self, test_regions, profile="default"):
        test_region_list = list(test_regions.values())
        ec2_client = self.boto3_cache.client("ec2", region="us-east-1", profile=profile)
        region_result = ec2_client.describe_regions()
        taskcat_id = test_region_list[0].taskcat_id

        all_region_names = [x["RegionName"] for x in region_result["Regions"]]
        existing_region_names = [x.name for x in test_region_list]
        regions_missing_but_needed = [
            x for x in all_region_names if x not in existing_region_names
        ]
        # Accounting for regions that may not be in a taskcat config file
        for region_name_to_add in regions_missing_but_needed:
            region_object = RegionObj(
                name=region_name_to_add,
                account_id=self.boto3_cache.account_id(profile),
                partition=self.boto3_cache.partition(profile),
                profile=profile,
                _boto3_cache=self.boto3_cache,
                taskcat_id=taskcat_id,
            )
            test_regions[region_name_to_add] = region_object

        final_regions = {
            region_name: region_object
            for region_name, region_object in test_regions.items()
            if region_name in all_region_names
        }

        return final_regions

    def _determine_templates_regions(self):
        templates = []
        codenames = set()

        LOG.info("Determining templates and supported regions")

        templates = self._determine_templates_regions()

        LOG.info("Determining regional search params for each AMI")
        # Flush out codenames.
        for template in templates:
            template_cn = build_codenames(template, Config)
            for tcn in template_cn:
                codenames.add(tcn)

        # Retrieve API Results.
        LOG.info("Retreiving results from the EC2 API")
        results = query_codenames(codenames, self.regions)

        LOG.info("Determining the latest AMI for each Codename/Region")
        updated_api_results = reduce_api_results(results)

        # Figure out a way to sort dictionary by key-value (timestmap)
        _write_template = False
        for template in templates:
            for result in updated_api_results:
                changed = template.set_codename_ami(
                    result.codename, result.region, result.ami_id
                )
                if changed:
                    _write_template = True
            if _write_template:
                template.write()
        LOG.info("Templates updated as necessary")
        if _write_template:
            raise AMIUpdaterCommitNeededException

        LOG.info("Complete!")
