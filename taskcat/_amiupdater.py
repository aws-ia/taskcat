import dataclasses
import datetime
import logging
import re
from dataclasses import dataclass, field
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool
from typing import Dict, List, Set

import pkg_resources
import yaml  # pylint: disable=wrong-import-order

import dateutil.parser  # pylint: disable=wrong-import-order
from taskcat._cfn.template import Template as TCTemplate
from taskcat._common_utils import deep_get
from taskcat._dataclasses import RegionObj
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)

REGION_REGEX = re.compile(
    "((eu|ap|us|af|me|ca|cn|sa)-|(us-gov-))"
    "(north(east|west)?|south(east|west)?|central|east|west)-[0-9]",
    re.IGNORECASE,
)


class Config:
    raw_dict: dict = {"global": {"AMIs": {}}}
    codenames: Set[Dict[str, str]] = set()

    @classmethod
    def load(cls, file_name, configtype=None):
        with open(file_name, "r") as _f:
            try:
                cls.raw_dict = yaml.safe_load(_f)
            except yaml.YAMLError as e:
                LOG.error(f"[{file_name}] - YAML Syntax Error!")
                raise AMIUpdaterFatalException(str(e))
        try:
            for _x in cls.raw_dict.get("global").get("AMIs").keys():
                cls.codenames.add(_x)

        except Exception as e:
            LOG.error(
                f"{configtype} config file [{file_name}]" f"is not structured properly!"
            )
            LOG.error(f"{e}")
            raise AMIUpdaterFatalException(str(e))

    @classmethod
    def update_filter(cls, code_name):
        cls.raw_dict["global"]["AMIs"].update(code_name)

    @classmethod
    def get_filter(cls, code_name):
        _x = deep_get(cls.raw_dict, f"global/AMIs/{code_name}", {})
        return _x


@dataclass
class EC2FilterValue:
    # pylint: disable=invalid-name
    Name: str
    Values: List[str]


@dataclass
class APIResultsData:
    codename: str
    ami_id: str
    creation_date: int
    region: str
    custom_comparisons: bool = True

    def __lt__(self, other):
        # See Codenames.parse_api_results for notes on why this is here.
        if self.custom_comparisons:
            return self.creation_date < other.creation_date
        return object.__lt__(self, other)

    def __gt__(self, other):
        # See Codenames.parse_api_results for notes on why this is here.
        if self.custom_comparisons:
            return self.creation_date > other.creation_date
        return object.__gt__(self, other)


@dataclass
class RegionalCodename:
    # pylint: disable=invalid-name
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
                line_no = codename.start_mark.line
                if cnvalue == "":
                    if '""' in self._ls[line_no]:
                        cnvalue = '""'
                    elif "''" in self._ls[line_no]:
                        cnvalue = "''"
                self.region_codename_lineno[key] = {"line": line_no, "old": cnvalue}
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
        if old_ami == '""':
            new_ami = f'"{new_ami}"'
        new_record = re.sub(old_ami, new_ami, self._ls[line_no])
        self._ls[line_no] = new_record
        return True

    def write(self):
        self.underlying.raw_template = "\n".join(self._ls)
        self.underlying.write()


class AMIUpdaterFatalException(TaskCatException):
    """Raised when AMIUpdater experiences a fatal error"""

    def __init__(self, message=None):
        super(AMIUpdaterFatalException, self).__init__(message)
        self.message = message


class AMIUpdaterCommitNeededException(TaskCatException):
    def __init__(self, message=None):
        super(AMIUpdaterCommitNeededException, self).__init__(message)
        self.message = message


def _construct_filters(cname: str, config: Config) -> List[EC2FilterValue]:
    formatted_filters: List[EC2FilterValue] = []
    fetched_filters = config.get_filter(cname)
    formatted_filters = [EC2FilterValue(k, [v]) for k, v in fetched_filters.items()]
    if formatted_filters:
        formatted_filters.append(EC2FilterValue("state", ["available"]))
    return formatted_filters


def build_codenames(tobj: Template, config: Config) -> List[RegionalCodename]:
    """Builds regional codename objects"""

    built_cn = []
    filters = deep_get(tobj.underlying.template, tobj.metadata_path, {})
    mappings = deep_get(tobj.underlying.template, tobj.mapping_path, {})

    for cname, cfilters in filters.items():
        config.update_filter({cname: cfilters})

    for region, cndata in mappings.items():
        _missing_filters: Set[str] = set()
        if region == "AMI":
            continue
        if not REGION_REGEX.search(region):
            LOG.error(f"[{region}] is not a valid region. Please check your template!")
            raise AMIUpdaterFatalException
        if region in tobj.regions_without_creds:
            continue
        for cnname in cndata.keys():
            _filters = _construct_filters(cnname, config)
            if not _filters:
                if cnname not in _missing_filters:
                    _missing_filters.add(cnname)
                    LOG.warning(
                        f"No query parameters were found for: {cnname.upper()}.",
                        f"(Results for this codename are not possible.",
                    )
                continue
            region_cn = RegionalCodename(region=region, cn=cnname, filters=_filters)
            built_cn.append(region_cn)
    return built_cn


def query_codenames(
    codename_list: Set[RegionalCodename], region_dict: Dict[str, RegionObj]
):
    """Fetches AMI IDs from AWS"""

    if len(codename_list) == 0:
        raise AMIUpdaterFatalException(
            "No AMI filters were found. Nothing to fetch from the EC2 API."
        )

    def _per_codename_amifetch(region_dict, regional_cn):
        new_filters = []
        for _filter in regional_cn.filters:
            new_filters.append(dataclasses.asdict(_filter))
        image_results = (
            region_dict.get(regional_cn.region)
            .client("ec2")
            .describe_images(Filters=new_filters)["Images"]
        )
        return {
            "region": regional_cn.region,
            "cn": regional_cn.cn,
            "api_results": image_results,
        }

    for region in list(region_dict.keys()):
        _ = region_dict[region].client("ec2")

    pool = ThreadPool(len(region_dict))
    _p = partial(_per_codename_amifetch, region_dict)
    response = pool.map(_p, codename_list)
    return response


def _image_timestamp(raw_ts):
    return int(dateutil.parser.parse(raw_ts).timestamp())


def reduce_api_results(raw_results):
    unsorted_results = []
    missing_results = []
    final_results = []
    result_state = {}

    for query_result in raw_results:
        if query_result["api_results"]:
            cn_api_results_data = [
                APIResultsData(
                    query_result["cn"],
                    x["ImageId"],
                    _image_timestamp(x["CreationDate"]),
                    query_result["region"],
                )
                for x in query_result["api_results"]
            ]
            unsorted_results = cn_api_results_data + unsorted_results
        else:
            missing_results.append(query_result)

    if missing_results:
        LOG.warning(
            "No results were available for the following CODENAME / Region combination"
        )

    for missing_result in missing_results:
        LOG.warning(f"- f{missing_result['cn']} in {missing_result['region']}")

    sorted_results = sorted(unsorted_results, reverse=True)
    for _r in sorted_results:
        found_key = f"{_r.region}-{_r.codename}"
        already_found = result_state.get(found_key, False)
        if already_found:
            continue
        result_state[found_key] = True
        final_results.append(_r)
    return final_results


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

        for tc_template in self.template_list:
            _t = Template(
                underlying=tc_template, regions_with_creds=list(self.regions.keys())
            )
            templates.append(_t)

        regions_without_creds = set()
        regions_excluded = set()
        for template in templates:
            for region in template.regions_without_creds:
                if region in self.EXCLUDED_REGIONS:
                    regions_excluded.add(region)
                else:
                    regions_without_creds.add(region)

        if regions_excluded:
            LOG.info(
                "FYI - Your templates use the following regions,"
                "however no credentials were detected"
            )
            LOG.info(", ".join([r.upper() for r in regions_excluded]))
            LOG.info(
                "These regions are not within the default AWS Partition. Continuing..."
            )

        if regions_without_creds:
            LOG.error(
                "Your templates use the following regions"
                "and no credentials were detected for them"
            )
            LOG.error(", ".join([r.upper() for r in regions_without_creds]))
            LOG.error("This can lead to inconsistent results. Not querying the API.")
            LOG.error("Verify your taskcat auth config or opt-in region status")
            LOG.error("- https://aws-quickstart.github.io/taskcat/#global-config")
            LOG.error(
                "- https://docs.aws.amazon.com/general/latest/gr/rande-manage.html"
            )
            raise AMIUpdaterFatalException

        return templates

    def update_amis(self):
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
