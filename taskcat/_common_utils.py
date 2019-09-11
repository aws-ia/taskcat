import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional, Union

import boto3
from jsonschema import RefResolver, validate

from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)

S3_PARTITION_MAP = {
    "aws": "amazonaws.com",
    "aws-cn": "amazonaws.com.cn",
    "aws-us-gov": "amazonaws.com",
}

FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def region_from_stack_id(stack_id):
    return stack_id.split(":")[3]


def name_from_stack_id(stack_id):
    return stack_id.split(":")[5].split("/")[1]


def s3_url_maker(bucket, key, s3_client):
    location = s3_client.get_bucket_location(Bucket=bucket)["LocationConstraint"]
    url = (
        f"https://{bucket}.s3.amazonaws.com/{key}"
    )  # default case for us-east-1 which returns no location
    if location:
        domain = get_s3_domain(location)
        url = f"https://{bucket}.s3-{location}.{domain}/{key}"
    return url


def get_s3_domain(region, ssm_client=None):
    ssm_client = ssm_client if ssm_client else boto3.client("ssm")
    partition = ssm_client.get_parameter(
        Name=f"/aws/service/global-infrastructure/regions/{region}/partition"
    )["Parameter"]["Value"]
    return S3_PARTITION_MAP[partition]


def s3_bucket_name_from_url(url):
    return url.split("//")[1].split(".")[0]


def s3_key_from_url(url):
    return "/".join(url.split("//")[1].split("/")[1:])


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
        security_group = re_object.search(data_line)
        if security_group:
            return str(security_group.group())
        return str("Not-found")

    def parse_stack_info(self):
        """
        Returns a dictionary object containing the region and stack name.

        :return: Dictionary object containing the region and stack name

        """
        stack_info = {}
        region_re = re.compile(r"(?<=:)(.\w-.+(\w*)-\d)(?=:)")
        stack_name_re = re.compile(r"(?<=:stack/)(tCaT.*.)(?=/)")
        stack_info["region"] = self.regxfind(region_re, self.stack_name)
        stack_info["stack_name"] = self.regxfind(stack_name_re, self.stack_name)
        return stack_info


def exit_with_code(code, msg=""):
    if msg:
        LOG.error(msg)
    sys.exit(code)


def make_dir(path, ignore_exists=True):
    path = os.path.abspath(path)
    if ignore_exists and os.path.isdir(path):
        return
    os.makedirs(path)


def param_list_to_dict(original_keys):
    # Setup a list index dictionary.
    # - Used to give an Parameter => Index mapping for replacement.
    param_index = {}
    if not isinstance(original_keys, list):
        raise TaskCatException(
            'Invalid parameter file, outermost json element must be a list ("[]")'
        )
    for (idx, param_dict) in enumerate(original_keys):
        if not isinstance(param_dict, dict):
            raise TaskCatException(
                'Invalid parameter %s parameters must be of type dict ("{}")'
                % param_dict
            )
        if "ParameterKey" not in param_dict or "ParameterValue" not in param_dict:
            raise TaskCatException(
                f"Invalid parameter {param_dict} all items must "
                f"have both ParameterKey and ParameterValue keys"
            )
        key = param_dict["ParameterKey"]
        param_index[key] = idx
    return param_index


def absolute_path(path: Optional[Union[str, Path]]):
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
        if "installer" in instance_copy.keys():
            instance_copy["installer"] = tests_to_dict(instance_copy["installer"])
    schema_path = Path(__file__).parent.absolute() / "cfg"
    with open(schema_path / f"schema_{schema_name}.json", "r") as file_handle:
        schema = json.load(file_handle)
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


def merge_dicts(list_of_dicts):
    merged_dict = {}
    for single_dict in list_of_dicts:
        merged_dict = {**merged_dict, **single_dict}
    return merged_dict


def pascal_to_snake(pascal):
    sub = ALL_CAP_RE.sub(r"\1_\2", pascal)
    return ALL_CAP_RE.sub(r"\1_\2", sub).lower()
