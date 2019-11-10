# TODO: add type hints
# type: ignore
# TODO: fix lint issues
# pylint: skip-file
import datetime
import logging
import re
from multiprocessing.dummy import Pool as ThreadPool
from functools import partial

import pkg_resources
import requests
import yaml

from taskcat._common_utils import deep_get
from dataclasses import dataclass, field
from taskcat._dataclasses import RegionObj
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)

class AMIUpdaterFatalException(TaskCatException):
    """Raised when AMIUpdater experiences a fatal error"""
    def __init__(self, message=None):
        if message:
            print("{} {}".format(PrintMsg.ERROR, message))

class AMIUpdaterNoFiltersException(TaskCatException):
    def __init__(self, message=None):
        if message:
            print("{} {}".format(PrintMsg.ERROR, message))

class AMIUpdaterCommitNeededException(TaskCatException):
    pass

def build_codenames(tobj, config):
    """Builds regional codename objects"""

    def _construct_filters(cname):
        formatted_filters = []
        fetched_filters = config.get_filter(cname)
        formatted_filters = [
            {"Name": k, "Values": [v]} for k,v in fetched_filters.items()
        ]
        if formatted_filters:
            formatted_filters.append({"Name": "state", "Values": ["available"]})
        return formatted_filters

    built_cn = []
    filters = deep_get(tobj.underlying.template, tobj.metadata_path, default=dict())
    mappings = deep_get(tobj.underlying.template, tobj.mapping_path, default=dict())

    for cname, cfilters in filters.items():
        config.update_filters({cname: cfilters})

    for region, cndata in mappings.items():
        if region == 'AMI':
            continue
        for cnname in cndata.keys():
            _filters = _construct_filters(cnname)
            region_cn = RegionalCodename(region=region, cn=cnname, filters=_filters)
            built_cn.append(region_cn)
    return built_cn

def query_codenames(codename_list, region_dict):
    """Fetches AMI IDs from AWS"""

    if len(codename_list) == 0:
        raise AMIUpdaterFatalException(
            "No AMI filters were found. Nothing to fetch from the EC2 API."
        )

    def _per_codename_amifetch(region_dict, regional_cn):
        image_results = region_dict.get(regional_cn.region).client('ec2').describe_images(
                Filters=regional_cn.filters)['Images']
        return {'region': regional_cn.region, "cn": regional_cn.cn, "api_results": image_results}

    for region in list(region_dict.keys()):
        _ = region_dict[region].client('ec2')

    pool = ThreadPool(len(region_dict))
    p = partial(_per_codename_amifetch, region_dict)
    response = pool.map(p, codename_list)
    return response

def reduce_api_results(raw_results):
    def _image_timestamp(raw_ts):
        ts_int = datetime.datetime.strptime(raw_ts, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
        return int(ts_int)

    unsorted_results = []
    missing_results = []
    final_results = []
    result_state = {}

    for query_result in raw_results:
        if query_result['api_results']:
            cn_api_results_data =[ APIResultsData(
                query_result['cn'],
                x['ImageId'],
                _image_timestamp(x['CreationDate']),
                query_result['region']
                ) for x in query_result['api_results']
            ]
            unsorted_results = cn_api_results_data + unsorted_results
        else:
            missing_results.append(query_result)

    if missing_results:
        LOG.warning("No results were available for the following CODENAME / Region combination")

    for missing_result in missing_results:
        LOG.warning(f"- f{missing_result['cn']} in {region}")

    sorted_results = sorted(unsorted_results, reverse=True)
    for r in sorted_results:
        found_key = f"{r.region}-{r.codename}"
        already_found = result_state.get(found_key, False)
        if already_found:
            continue
        result_state[found_key] = True
        final_results.append(r)
    return final_results

class Config:
    raw_dict = {"global": {"AMIs": {}}}
    codenames = set()

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
            raise AMIUpdaterException

    @classmethod
    def update_filter(cls, dn):
        cls.raw_dict["global"]["AMIs"].update(dn)

    @classmethod
    def get_filter(cls, dn):
        x = deep_get(cls.raw_dict, f"global/AMIs/{dn}")
        return x

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
    new_ami: str = field(default_factory=str)
    filters: list = field(default_factory=list)
    _creation_dt = datetime.datetime.now()

    def __hash__(self):
        return hash(self.region+self.cn+ self.new_ami+str(self.filters))

class Template:
    #TODO: Type these
    def __init__(self, underlying, excluded_regions, regions_with_creds):
        self.codenames  = set()
        self.mapping_path = "Mappings/AWSAMIRegionMap"
        self.metadata_path = "Metadata/AWSAMIRegionMap/Filters"
        self.region_codename_lineno = {}
        self.region_names = set()
        self.underlying = underlying
        self._ls = self.underlying.linesplit
        _template_regions = deep_get(self.underlying.template, self.mapping_path, {})
        for region_name, region_data in _template_regions.items():
            if region_name == "AMI":
                continue
            self.region_names.add(region_name)
            for codename, cnvalue in region_data.items():
                key = f"{codename}/{region_name}"
                self.region_codename_lineno[key] = {
                        'line': codename.start_mark.line,
                        'old': cnvalue
                        }
        new_region_list = set()
        for region in self.region_names:
            if (region in excluded_regions) and (region not in regions_with_creds):
                continue
            new_region_list.add(region)
        self.region_names = new_region_list

    def set_codename_ami(self, cname, region, new_ami):
        if region not in self.region_names:
            return False
        key = f"{cname}/{region}"
        try:
            line_no = self.region_codename_lineno[key]['line']
            old_ami = self.region_codename_lineno[key]['old']
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
        self.regions = self._determine_testable_regions(regions)
        self.boto3_cache = boto3cache

    @classmethod
    def check_updated_upstream_mapping_spec(cls):
        # TODO: add v9 compatible logic to check versions
        return False

    @classmethod
    def update_upstream_mapping_spec(cls):
        r = requests.get(cls.upstream_config_file_url)
        if r.ok:
            with open(cls.upstream_config_file) as f:
                f.write(r.content)


    #TODO FIXME
    def list_unknown_mappings(self):
        pass
#        for template_file in self._fetch_template_files():
#            TemplateObject(template_file)
#
#        unknown_mappings = Codenames.unknown_mappings()
#        if unknown_mappings:
#            LOG.warning(
#                "The following mappings are unknown to AMIUpdater. Please investigate"
#            )
#            for unknown_map in unknown_mappings:
#                LOG.warning(unknown_map)
#

    def _determine_testable_regions(self, test_regions, profile='default'):
        test_region_list = list(test_regions.values())
        ec2_client = self.boto3_cache.client('ec2', region='us-east-1', profile=profile)
        region_result = ec2_client.describe_regions()
        taskcat_id = test_region_list[0].taskcat_id

        all_region_names = [x['RegionName'] for x in region_result['Regions']]
        existing_region_names = [x.name for x in test_region_list]
        regions_missing_but_needed = [x for x in all_region_names if x not in existing_region_names]
        # Accounting for regions that may not be in a taskcat config file
        for region_name_to_add in regions_missing_but_needed:
            region_object = RegionObj(
                name=region_name_to_add,
                account_id=self.boto3_cache.account_id(profile),
                partition=self.boto3_cache.partition(profile),
                profile=profile,
                _boto3_cache=self.boto3_cache,
                taskcat_id=taskcat_id
            )
            test_regions[region_name_to_add] = region_object

        # Accounting for regions that are present in a taskcat config file, but we don't have access to
        # ex: opt-in regions, etc.

        final_regions = {region_name: region_object for region_name, region_object in test_regions.items() if
                         region_name in all_region_names}

        return final_regions

    def update_amis(self):
        templates = []
        regions = []
        codenames = set()
        _regions_with_creds = self.regions.keys()

        LOG.info("Determining templates and supported regions")
        # Flush out templates and supported regions
        for tc_template in self.template_list:
            _t = Template(underlying=tc_template,
                          excluded_regions=self.EXCLUDED_REGIONS,
                          regions_with_creds=_regions_with_creds)
            templates.append(_t)

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
                changed = template.set_codename_ami(result.codename, result.region, result.ami_id)
                if changed:
                    _write_template = True
            if _write_template:
                template.write()
        LOG.info("Templates updated as necessary")

        LOG.info("Complete!")
