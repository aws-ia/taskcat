import collections
import logging
import os
import re
import sys
from collections import OrderedDict
from functools import reduce
from pathlib import Path
from time import sleep

import requests
import yaml
from botocore.exceptions import ClientError

from dulwich.config import ConfigFile, parse_submodules
from taskcat.exceptions import TaskCatException
from taskcat.regions_to_partitions import REGIONS

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


def s3_url_maker(bucket, key, s3_client, autobucket=False):
    retries = 10
    while True:
        try:
            try:
                response = s3_client.get_bucket_location(Bucket=bucket)
                location = response["LocationConstraint"]
            except ClientError as e:
                if e.response["Error"]["Code"] != "AccessDenied":
                    raise
                resp = requests.get(f"https://{bucket}.s3.amazonaws.com/{key}")
                location = resp.headers.get("x-amz-bucket-region")
                if not location:
                    # pylint: disable=raise-missing-from
                    raise TaskCatException(
                        f"failed to discover region for bucket {bucket}"
                    )
            break
        except s3_client.exceptions.NoSuchBucket:
            if not autobucket or retries < 1:
                raise
            retries -= 1
            sleep(5)

    # default case for us-east-1 which returns no location
    url = f"https://{bucket}.s3.us-east-1.amazonaws.com/{key}"
    if location:
        domain = get_s3_domain(location)
        url = f"https://{bucket}.s3.{location}.{domain}/{key}"
    return url


def get_s3_domain(region):
    try:
        return S3_PARTITION_MAP[REGIONS[region]]
    except KeyError:
        # pylint: disable=raise-missing-from
        raise TaskCatException(f"cannot find the S3 hostname for region {region}")


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
        # pylint: disable=raise-missing-from
        raise TaskCatException(
            'Invalid parameter file, outermost json element must be a list ("[]")'
        )
    for (idx, param_dict) in enumerate(original_keys):
        if not isinstance(param_dict, dict):
            # pylint: disable=raise-missing-from
            raise TaskCatException(
                'Invalid parameter %s parameters must be of type dict ("{}")'
                % param_dict
            )
        if "ParameterKey" not in param_dict or "ParameterValue" not in param_dict:
            # pylint: disable=raise-missing-from
            raise TaskCatException(
                f"Invalid parameter {param_dict} all items must "
                f"have both ParameterKey and ParameterValue keys"
            )
        key = param_dict["ParameterKey"]
        param_index[key] = idx
    return param_index


def merge_dicts(list_of_dicts):
    merged_dict = {}
    for single_dict in list_of_dicts:
        merged_dict = {**merged_dict, **single_dict}
    return merged_dict


def pascal_to_snake(pascal):
    sub = ALL_CAP_RE.sub(r"\1_\2", pascal)
    return ALL_CAP_RE.sub(r"\1_\2", sub).lower()


def merge_nested_dict(old, new):
    for k, v in new.items():
        if isinstance(old.get(k), dict) and isinstance(v, collections.Mapping):
            merge_nested_dict(old[k], v)
        else:
            old[k] = v


def ordered_dump(data, stream=None, dumper=yaml.Dumper, **kwds):
    class OrderedDumper(dumper):  # pylint: disable=too-many-ancestors
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items()
        )

    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def deep_get(dictionary, keys, default=None):
    zulu = reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        keys.split("/"),
        dictionary,
    )
    return zulu


def neglect_submodule_templates(project_root, template_list):
    template_dict = {}
    # one template object per path.
    for template in template_list:
        template_dict[template.template_path] = template
        for template_descendent in template.descendents:
            template_dict[template_descendent.template_path] = template_descendent

    # Removing those within a submodule.
    submodule_path_prefixes = []
    try:
        gitmodule_config = ConfigFile.from_path(Path(project_root / ".gitmodules"))
    except FileNotFoundError:
        return template_list

    for submodule_path, _, _ in parse_submodules(gitmodule_config):
        submodule_path_prefixes.append(
            Path(project_root / submodule_path.decode("utf-8"))
        )

    finalized_templates = []
    for template_obj in list(template_dict.values()):
        gitmodule_template = False
        for gm_path in submodule_path_prefixes:
            if gm_path in template_obj.template_path.parents:
                gitmodule_template = True
        if not gitmodule_template:
            finalized_templates.append(template_obj)
    return finalized_templates


def determine_profile_for_region(auth_dict, region):
    profile = auth_dict.get(region, auth_dict.get("default", "default"))
    return profile


def fetch_ssm_parameter_value(boto_client, parameter_path):
    ssm = boto_client("ssm")
    response = ssm.get_parameter(Name=parameter_path)
    return response["Parameter"]["Value"]


def fetch_secretsmanager_parameter_value(boto_client, secret_arn):
    secrets_manager = boto_client("secretsmanager")
    try:
        response = secrets_manager.get_secret_value(SecretId=secret_arn)["SecretString"]
    except Exception as e:
        # pylint: disable=raise-missing-from
        raise TaskCatException(
            "ARN: {} encountered an error: {}".format(secret_arn, str(e))
        )
    return response
