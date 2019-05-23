import re
import sys
import os
import logging
from pathlib import Path
import json
from jsonschema import RefResolver, validate
from taskcat.exceptions import TaskCatException

log = logging.getLogger(__name__)

S3_PARTITION_MAP = {
    'aws': 'amazonaws.com',
    'aws-cn': 'amazonaws.com.cn',
    'aws-us-gov': 'amazonaws.com'
}


def region_from_stack_id(stack_id):
    return stack_id.split(':')[3]


def name_from_stack_id(stack_id):
    return stack_id.split(':')[5].split('/')[1]


def s3_url_maker(bucket, key, client_factory):
    s3_client = client_factory.get('s3')
    location = s3_client.get_bucket_location(Bucket=bucket)['LocationConstraint']
    url = f'https://{bucket}.s3.amazonaws.com/{key}'  # default case for us-east-1 which returns no location
    if location:
        domain = get_s3_domain(location, client_factory)
        url = f'https://{bucket}.s3-{location}.{domain}/{key}'
    return url


def get_s3_domain(region, client_factory):
    ssm_client = client_factory.get('ssm')
    partition = ssm_client.get_parameter(
        Name=f'/aws/service/global-infrastructure/regions/{region}/partition'
    )["Parameter"]["Value"]
    return S3_PARTITION_MAP[partition]


def s3_bucket_name_from_url(url):
    return url.split('//')[1].split('.')[0]


def s3_key_from_url(url):
    return '/'.join(url.split('//')[1].split('/')[1:])


class CommonTools:

    def __init__(self, stack_name):
        self.stack_name = stack_name

    @staticmethod
    def regxfind(re_object, data_line):
        """
        Returns the matching string.

        :param re_object: Regex object
        :param data_line: String to be searched

        :return: Matching String if found, otherwise return 'Not-found'
        """
        sg = re_object.search(data_line)
        if sg:
            return str(sg.group())
        else:
            return str('Not-found')

    def parse_stack_info(self):
        """
        Returns a dictionary object containing the region and stack name.

        :return: Dictionary object containing the region and stack name

        """
        stack_info = dict()
        region_re = re.compile(r'(?<=:)(.\w-.+(\w*)-\d)(?=:)')
        stack_name_re = re.compile(r'(?<=:stack/)(tCaT.*.)(?=/)')
        stack_info['region'] = self.regxfind(region_re, self.stack_name)
        stack_info['stack_name'] = self.regxfind(stack_name_re, self.stack_name)
        return stack_info


def exit1(msg=''):
    if msg:
        log.error(msg)
    sys.exit(1)


def exit0(msg=''):
    if msg:
        log.info(msg)
    sys.exit(0)


def make_dir(path, ignore_exists=True):
    path = os.path.abspath(path)
    if ignore_exists and os.path.isdir(path):
        return
    os.makedirs(path)


def param_list_to_dict(original_keys):
    # Setup a list index dictionary.
    # - Used to give an Parameter => Index mapping for replacement.
    param_index = {}
    if type(original_keys) != list:
        raise TaskCatException('Invalid parameter file, outermost json element must be a list ("[]")')
    for (idx, param_dict) in enumerate(original_keys):
        if type(param_dict) != dict:
            raise TaskCatException('Invalid parameter %s parameters must be of type dict ("{}")' % param_dict)
        if 'ParameterKey' not in param_dict or 'ParameterValue' not in param_dict:
            raise TaskCatException(
                'Invalid parameter %s all items must have both ParameterKey and ParameterValue keys' % param_dict)
        key = param_dict['ParameterKey']
        param_index[key] = idx
    return param_index


def buildmap(start_location, map_string, partial_match=True):
    """
    Given a start location and a string value, this function returns a list of
    file paths containing the given string value, down in the directory
    structure from the start location.

    :param start_location: directory from where to start looking for the file
    :param map_string: value to match in the file path
    :param partial_match: (bool) Turn on partial matching.
    :  Ex: 'foo' matches 'foo' and 'foo.old'. Defaults true. False adds a '/' to the end of the string.
    :return:
        list of file paths containing the given value.
    """
    if not partial_match:
        map_string = "{}/".format(map_string)
    fs_map = []
    for fs_path, dirs, filelist in os.walk(start_location, topdown=False):
        for fs_file in filelist:
            fs_path_to_file = (os.path.join(fs_path, fs_file))
            if map_string in fs_path_to_file and '.git' not in fs_path_to_file:
                fs_map.append(fs_path_to_file)
    return fs_map


def absolute_path(path: [str, Path]):
    if path is None:
        return None
    path = Path(path).expanduser().resolve()
    if not path.exists():
        return None
    return path


def schema_validate(instance, schema_name):
    instance_copy = instance.copy()
    if isinstance(instance_copy, dict):
        if "tests" in instance_copy.keys():
            instance_copy["tests"] = tests_to_dict(instance_copy["tests"])
    schema_path = Path(__file__).parent.absolute() / "cfg"
    schema = json.load(open(schema_path / f"schema_{schema_name}.json", "r"))
    validate(
        instance_copy,
        schema,
        resolver=RefResolver(str(schema_path.as_uri()) + "/", None),
    )


def tests_to_dict(tests):
    rendered_tests = {}
    for test in tests.keys():
        rendered_tests[test] = {}
        for k, v in tests[test].__dict__.items():
            if not k.startswith("_"):
                if isinstance(v, Path):
                    v = str(v)
                rendered_tests[test][k] = v
    return rendered_tests
