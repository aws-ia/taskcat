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
from taskcat._client_factory import Boto3Cache
from taskcat._common_utils import deep_get, neglect_submodule_templates
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
                # pylint: disable=raise-missing-from
                raise AMIUpdaterFatalException(str(e))
        try:
            for _x in cls.raw_dict.get("global").get("AMIs").keys():
                cls.codenames.add(_x)

        except Exception as e:
            LOG.error(
                f"{configtype} config file [{file_name}]" f"is not structured properly!"
            )
            LOG.error(f"{e}")
            # pylint: disable=raise-missing-from
            raise AMIUpdaterFatalException(str(e))

    @classmethod
    def update_filter(cls, code_name):
        cls.raw_dict["global"]["AMIs"].update(code_name)

    @classmethod
    def get_filter(cls, code_name):
        _x = deep_get(cls.raw_dict, f"global/AMIs/{code_name}", {})
        return {
            str(k): [str(v)] if isinstance(v, str) else list(v) for k, v in _x.items()
        }


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
    def __init__(self, underlying: TCTemplate):
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
        # pylint: disable=super-with-arguments
        super(AMIUpdaterFatalException, self).__init__(message)
        self.message = message


class AMIUpdaterCommitNeededException(TaskCatException):
    def __init__(self, message=None):
        # pylint: disable=super-with-arguments
        super(AMIUpdaterCommitNeededException, self).__init__(message)
        self.message = message


def _construct_filters(cname: str, config: Config) -> List[EC2FilterValue]:
    formatted_filters: List[EC2FilterValue] = []
    fetched_filters = config.get_filter(cname)
    formatted_filters = [EC2FilterValue(k, v) for k, v in fetched_filters.items()]
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
        for cnname in cndata.keys():
            _filters = _construct_filters(cnname, config)
            if not _filters:
                if cnname not in _missing_filters:
                    _missing_filters.add(cnname)
                    LOG.warning(
                        f"No query parameters were found for: {cnname.upper()}.",
                        "(Results for this codename are not possible.",
                    )
                continue
            region_cn = RegionalCodename(region=region, cn=cnname, filters=_filters)
            built_cn.append(region_cn)
    return built_cn


def _per_codename_amifetch(region_dict, regional_cn):
    new_filters = []
    for _filter in regional_cn.filters:
        new_filters.append(dataclasses.asdict(_filter))
    _r = region_dict.get(regional_cn.region)
    image_results = []
    if _r:
        image_results = _r.client("ec2").describe_images(Filters=new_filters)["Images"]
    return {
        "region": regional_cn.region,
        "cn": regional_cn.cn,
        "api_results": image_results,
    }


def query_codenames(
    codename_list: Set[RegionalCodename], region_dict: Dict[str, RegionObj]
):
    """Fetches AMI IDs from AWS"""

    if len(codename_list) == 0:
        raise AMIUpdaterFatalException(
            "No AMI filters were found. Nothing to fetch from the EC2 API."
        )

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
        LOG.warning(f"- {missing_result['cn']} in {missing_result['region']}")

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
        "taskcat/main/cfg/amiupdater.cfg.yml"
    )

    def __init__(self, config, user_config_file=None, use_upstream_mappings=True):
        if use_upstream_mappings:
            Config.load(self.upstream_config_file, configtype="Upstream")
        if user_config_file:
            Config.load(user_config_file, configtype="User")
        # TODO: Needed?
        self.config = config
        self.boto3_cache = Boto3Cache()
        self.template_list = self._determine_templates()
        self.regions = self._get_regions()

    def _get_regions(self):
        profile = (
            self.config.config.general.auth.get("default", "default")
            if self.config.config.general.auth
            else "default"
        )
        default_region = self.boto3_cache.get_default_region(profile)
        regions = [
            _r["RegionName"]
            for _r in self.boto3_cache.client(
                "ec2", profile, default_region
            ).describe_regions()["Regions"]
        ]
        regions = self.get_regions_for_profile(profile, regions)
        if self.config.config.general.auth:
            for region, profile in self.config.config.general.auth.items():
                regions.update(self.get_regions_for_profile(profile, [region]))
        return regions

    def get_regions_for_profile(self, profile, _regions):
        regions = {}
        for _r in _regions:
            regions[_r] = RegionObj(
                name=_r,
                account_id=self.boto3_cache.account_id(profile),
                partition=self.boto3_cache.partition(profile),
                profile=profile,
                _boto3_cache=self.boto3_cache,
                taskcat_id=self.config.uid,
                _role_name=None,
            )
        return regions

    def _determine_templates(self):
        _up = self.config.get_templates()
        unprocessed_templates = list(_up.values())
        finalized_templates = neglect_submodule_templates(
            project_root=self.config.project_root, template_list=unprocessed_templates
        )
        return finalized_templates

    def _determine_templates_regions(self):
        templates = []

        for tc_template in self.template_list:
            _t = Template(underlying=tc_template)
            templates.append(_t)

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
        LOG.info("Retrieving results from the EC2 API")
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
        if _write_template:
            LOG.info("Templates updated")
            raise AMIUpdaterCommitNeededException

        LOG.info("No AMI's needed updates.")
