import collections
import os
import json
import datetime
import pkg_resources
import requests
import yaml
import re
from functools import reduce
from taskcat.client_factory import ClientFactory
from taskcat.utils import CFNYAMLHandler as cfy
from taskcat.colored_console import PrintMsg
from taskcat.stacker import TaskCat as tc
from multiprocessing.dummy import Pool as ThreadPool


class AMIUpdaterException(Exception):
    """Raised when AMIUpdater experiences a fatal error"""
    pass


class APIResultsData(object):
    results = []

    def __init__(self, codename, ami_id, creation_date, region, custom_comparisons=True, *args, **kwargs):
        self.codename = codename
        self.ami_id = ami_id
        self.creation_date = creation_date
        self.region = region
        self.custom_comparisons = custom_comparisons

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


class Config:
    raw_dict = {'global': {'AMIs':{}}}
    codenames = set()

    @classmethod
    def load(cls, fn, configtype=None):
        with open(fn, 'r') as f:
            try:
                cls.raw_dict = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print("{} [{}] - YAML Syntax Error!").format(PrintMsg.ERROR, fn)
                print("{} {}".format(PrintMsg.ERROR, e))
        try:
            for x in cls.raw_dict.get('global').get('AMIs').keys():
                cls.codenames.add(x)
        except Exception as e:
            print("{} {} config file [{}] is not structured properly!".format(PrintMsg.ERROR, configtype, fn))
            print("{}\t{}".format(PrintMsg.ERROR, e))
            raise AMIUpdaterException


    @classmethod
    def update_filter(cls, dn):
        cls.raw_dict['global']['AMIs'].update(dn)


class Codenames:
    filters = None
    _objs = {}
    _no_filters = {}

    def __new__(cls, *args, **kwargs):
        if args[0] in cls._objs.keys():
            instance = cls._objs.get(args[0])
            if args[0] in cls._no_filters.keys():
                del cls._no_filters[args[0]]
        elif args[0] in cls._no_filters.keys():
            instance = cls._objs.get(args[0])
        else:
            instance = super(Codenames).__init__(cls)
        return instance

    def __init__(self, cn, *args, **kwargs):
        self.cn = cn
        self._regions = set()
        self._region_data = set()
        if self._create_codename_filters():
            self._objs[cn] = self
        else:
            self._no_filters[cn] = self

    def _create_codename_filters(self):
        # I'm grabbing the filters from the config file, and adding them to self.filters;
        # The RegionalCodename instance can access this value. That's important for threading
        # the API queries - which we do.
        cnfilter = TemplateClass.deep_get(Config.raw_dict, "global/AMIs/{}".format(self.cn))
        if self._filters:
            cnfilter = self._filters
        if cnfilter:
            self.filters = [{'Name':k, 'Values': [v]} for k, v in cnfilter.items()]
            self.filters.append({'Name':'state', 'Values':['available']})
        if not self.filters:
            return None
        return True

    def regions(self):
        return list(self._regions)

    @classmethod
    def objects(cls):
        return list(cls._objs.values())

    @classmethod
    def unknown_mappings(cls):
        return cls._no_filters.keys()

    @classmethod
    def fetch_latest_amis(cls):
        """Fetches AMI IDs from AWS"""
        # This is a wrapper for the threaded run.
        # Create a ThreadPool, size is the number of regions.

        if len(RegionalCodename.objects()) == 0:
            raise AMIUpdaterException("No AMI filters were found. Nothing to fetch from the EC2 API.")

        pool = ThreadPool(len(TemplateClass.regions()))
        # For reach RegionalCodename that we've generated....
        pool.map(cls._per_rcn_ami_fetch, RegionalCodename.objects())

    @classmethod
    def _per_rcn_ami_fetch(cls, rcn):
        rcn.results = AMIUpdater.client_factory.get('ec2', rcn.region).describe_images(Filters=rcn.filters)['Images']

    @classmethod
    def parse_api_results(cls):
        raw_ami_names = {}
        region_codename_result_list = []
        missing_results_list = []

        # For each RegionalCodename.
        #     Create a Dictionary like so:
        #     CODENAME
        #       - REGION_NAME
        #           [{RAW_API_RESULTS_1}, {RAW_API_RESULTS_2}, {RAW_API_RESULTS_N}]
        for rcn in RegionalCodename.objects():
            if rcn.cn in raw_ami_names.keys():
                raw_ami_names[rcn.cn][rcn.region] = [
                    APIResultsData(rcn.cn, x['ImageId'],
                                   int(datetime.datetime.strptime(x['CreationDate'],
                                                                  "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()), rcn.region)
                    for x in rcn.results]
            else:
                raw_ami_names.update({rcn.cn:
                                          {rcn.region: [APIResultsData(rcn.cn, x['ImageId'],
                                                                       int(datetime.datetime.strptime(x['CreationDate'],
                                                                                                      "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()), rcn.region)
                                                        for x in rcn.results]}})

        for codename, regions in raw_ami_names.items():
            for region, results_list in regions.items():
                if len(results_list) == 0:
                    missing_results_list.append((codename, region))
                    continue
                latest_ami = sorted(results_list, reverse=True)[0]
                latest_ami.custom_comparisons = False
                region_codename_result_list.append(latest_ami)
        if missing_results_list:
            for code_reg in missing_results_list:
                print("{} The following Codename / Region  had no results from the EC2 API. {}".format(PrintMsg.ERROR, code_reg))
            raise AMIUpdaterException("One or more filters returns no results from the EC2 API.")
        APIResultsData.results = region_codename_result_list


class RegionalCodename(Codenames):
    _x = {}

    def __new__(cls, *args, **kwargs):
        # A word on this.
        # - An instance of RegionalCodename is a representation of CODENAME and AMINAME.
        # Since this module allows for multiple templates, *and* interrogates all templates at once,
        # there's a risk I could end up with multiple instantations for each CODENAME/AMINAME combination.
        # I maintain a dictionary of CODENAMEREGION -> Instance mappings, so if this class is instantated with the same
        # arguments twice, the exact same memory pointer is returned.
        try:
            region = kwargs.get('region')
            cn = kwargs.get('cn')
        except KeyError:
            raise
        k = "{}{}".format(cn,region)
        if k in cls._x.keys():
            instance = cls._x.get(k)
        else:
            instance = super(Codenames, cls).__new__(cls)
            cls._x[k] = instance
        return instance

    @classmethod
    def objects(cls):
        return [z for z in cls._x.values() if z.filters]

    def __init__(self, cn, region, filters=None, *args, **kwargs):
        self.region = region
        self.results = None
        self._filters = filters
        super(RegionalCodename, self).__init__(cn, region, *args, **kwargs)


class TemplateClass(object):
    mapping_path = "Mappings/AWSAMIRegionMap"
    metadata_path = "Metadata/AWSAMIRegionMap/Filters"
    template_ext = ['.template', '.json', '.yaml', '.yml']
    _regions = set()
    _codenames = set()

    @staticmethod
    def deep_get(dictionary, keys, default=None):
        zulu = reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("/"),
                      dictionary)
        return zulu

    @staticmethod
    def deep_set(dictionary, keys, value):
        for key in keys.split('/')[:-1]:
            dictionary = dictionary.setdefault(key, {})

    @classmethod
    def regions(cls):
        return [x for x in list(cls._regions) if x is not 'AMI']

    @staticmethod
    def _fetch_contents(filename):
        """Loads the template to inspect"""
        with open(filename) as f:
            tfdata = f.read()
        stripped_tfdata = tfdata.strip()
        if stripped_tfdata[0] in ['{', '['] and stripped_tfdata[-1] in ['}', ']']:
            filetype = 'json'
            loaded_template_data = json.loads(tfdata, object_pairs_hook=collections.OrderedDict)
        else:
            filetype = 'yaml'
            loaded_template_data = cfy.ordered_safe_load(open(filename, 'rU'), object_pairs_hook=collections.OrderedDict)
        return filetype, loaded_template_data, tfdata



class TemplateObject(TemplateClass):
    _objs = []
    replacement_ami_map = {}

    @classmethod
    def objects(cls):
        return cls._objs

    def __init__(self, filename, all_regions=False):
        self._filename = filename
        self.filetype, self._contents, self._raw = self._fetch_contents(filename)
        self._mapping_root = self.deep_get(self._contents, self.mapping_path)
        self.filter_metadata = self.deep_get(self._contents, self.metadata_path)
        self.all_regions = all_regions
        self.filters = None
        self.codename = None
        
        # This is where we know the instantation is good (we've passed sanity checks).
        # Looking for Mappings/AWSAMIRegionMap
        if not self._mapping_root:
            return None

        # Sort out what regions are being used. 
        self._determine_regions()

        # Appending the object so it can be referenced later.
        self._objs.append(self)

        # Generate RegionalCodename filters based on what's in the template. 
        self._generate_regional_codenames()

    def _generate_regional_codenames(self):
        for region in self._regions:
            if region == 'AMI':
                continue
            if self.filter_metadata:
                for k in self.filter_metadata.keys():
                    RegionalCodename(cn=k, region=region, filters=self.filter_metadata[k])
            else:
                # Region Name, Latest AMI Name in Template
                # - We instantiate them in the RegionalCodename class
                #   because it allows us to access the attributes as an object.
                #   It also generates the Filters needed in each API call.
                #   - This is done in the Codenames class, so check that out.
                try:
                    for k in self._mapping_root[region].keys():
                        RegionalCodename(cn=k, region=region)
                except KeyError:
                    pass

    def _determine_regions(self):
        self._region_list = list()
        _ec2_regions = AMIUpdater.client_factory.get('ec2', 'us-east-1').describe_regions()['Regions']
        for _ec2r in _ec2_regions:
            self._region_list.append(_ec2r['RegionName'])
        if self.all_regions:
            for region in self._region_list:
                self._regions.add(region)
        else:
            # Use the regions that are in Mappings/AWSAMIRegionMap
            for region in self._mapping_root.keys():
                if region == 'AMI':
                    continue
                if region not in self._region_list:
                    if region in AMIUpdater.EXCLUDED_REGIONS:
                        print("{} The {} region is currently unsupported. AMI IDs will not be updated for this region.".format(PrintMsg.ERROR, region))
                    else:
                        raise AMIUpdaterException("Template: [{}] Region: [{}] is not a valid region".format(self._filename, region))
                self._regions.add(region)

    def set_region_ami(self, cn, region, ami_id):
        currvalue = self._contents['Mappings']['AWSAMIRegionMap'].get(region, None).get(cn, None)
        if currvalue:
            self.replacement_ami_map[currvalue] = ami_id

    def rotate_ami_id(self, old_ami, new_ami):
        self._raw = re.sub(old_ami, new_ami, self._raw)

    def write(self):
        for old_ami, new_ami in self.replacement_ami_map.items():
            self.rotate_ami_id(old_ami, new_ami)

        with open(self._filename, 'w') as updated_template:
            updated_template.write(self._raw)


class AMIUpdater:
    client_factory = None
    upstream_config_file = pkg_resources.resource_filename('taskcat', '/cfg/amiupdater.cfg.yml')
    upstream_config_file_url = "https://raw.githubusercontent.com/aws-quickstart/taskcat/master/cfg/amiupdater.cfg.yml"
    EXCLUDED_REGIONS = [
            'us-gov-east-1',
            'us-gov-west-1',
            'cn-northwest-1',
            'cn-north-1'
    ]

    def __init__(self, path_to_templates, user_config_file=None,
                 use_upstream_mappings=True, client_factory=None):
        if client_factory:
            AMIUpdater.client_factory = client_factory
        else:
            AMIUpdater.client_factory = ClientFactory()
        self.all_regions = False
        if use_upstream_mappings:
            Config.load(self.upstream_config_file, configtype='Upstream')
        if user_config_file:
            Config.load(user_config_file, configtype='User')
        self._template_path = path_to_templates

    def _load_config_file(self):
        """Loads the AMIUpdater Config File"""
        with open(self._user_config_file) as f:
            config_contents = yaml.safe_load(f)
        self.config = config_contents

    def _fetch_template_files(self):
        p = self._template_path
        if os.path.isfile(p):
            yield p
        elif os.path.isdir(p):
            for dirpath, dirname, file_names in os.walk(p):
                for fn in file_names:
                    if fn.endswith(tuple(TemplateClass.template_ext)):
                        yield os.path.join(dirpath, fn)

    @classmethod
    def check_updated_upstream_mapping_spec(cls):
        needed, version = tc.checkforupdate(True)
        if needed:
            return version
        return False

    @classmethod
    def update_upstream_mapping_spec(cls):
        r = requests.get(cls.upstream_config_file_url)
        if r.ok:
            with open(cls.upstream_config_file) as f:
                f.write(r.content)

    def list_unknown_mappings(self):
        for template_file in self._fetch_template_files():
            TemplateObject(template_file)

        unknown_mappings = Codenames.unknown_mappings()
        if unknown_mappings:
            print("{} The following mappings are unknown to AMIUpdater. Please investigate".format(PrintMsg.INFO))
            for unknown_map in unknown_mappings:
                print(unknown_map)

    def update_amis(self):
        for template_file in self._fetch_template_files():
            # Loads each template as an object.
            TemplateObject(template_file)
        print("{} Created all filters necessary for the API calls".format(PrintMsg.INFO))
        # Fetches latest AMI IDs from the API.
        # Determines the most common AMI names across all regions
        # Sorts the AMIs by creation date, results go into APIResultsData.results.
        # - See APIResultsData class and Codenames.parse_api_results function for details.
        Codenames.fetch_latest_amis()
        print("{} Latest AMI IDs fetched".format(PrintMsg.INFO))
        Codenames.parse_api_results()
        print("{} API results parsed".format(PrintMsg.INFO))

        for template_object in TemplateObject.objects():
            for result in APIResultsData.results:
                template_object.set_region_ami(result.codename, result.region, result.ami_id)

        # For each template, write it to disk.
        for template_object in TemplateObject.objects():
            template_object.write()
        print("{} Templates updated as necessary".format(PrintMsg.INFO))
        print("{} Complete!".format(PrintMsg.INFO))
