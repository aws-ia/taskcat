"""
TaskCat Common Utilities Module

This module provides a collection of utility functions and classes used throughout
the TaskCat application. It includes functions for:

- AWS resource manipulation (S3, CloudFormation, SSM, Secrets Manager)
- String and data structure processing
- File system operations
- URL parsing and construction
- Configuration management
- Git submodule handling

These utilities support the core TaskCat functionality by providing reusable
components for common operations across different modules.
"""

import collections.abc
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

# Initialize module logger
LOG = logging.getLogger(__name__)

# Mapping of AWS partitions to their S3 domain suffixes
S3_PARTITION_MAP = {
    "aws": "amazonaws.com",           # Standard AWS partition
    "aws-cn": "amazonaws.com.cn",     # AWS China partition
    "aws-us-gov": "amazonaws.com",    # AWS GovCloud partition
}

# Regular expressions for converting PascalCase to snake_case
FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def region_from_stack_id(stack_id):
    """
    Extract the AWS region from a CloudFormation stack ID.
    
    CloudFormation stack IDs follow the format:
    arn:aws:cloudformation:region:account-id:stack/stack-name/unique-id
    
    Args:
        stack_id (str): The CloudFormation stack ID/ARN
        
    Returns:
        str: The AWS region code (e.g., 'us-east-1', 'eu-west-1')
        
    Example:
        >>> stack_id = "arn:aws:cloudformation:us-east-1:123456789012:stack/my-stack/abc123"
        >>> region_from_stack_id(stack_id)
        'us-east-1'
    """
    return stack_id.split(":")[3]


def name_from_stack_id(stack_id):
    """
    Extract the stack name from a CloudFormation stack ID.
    
    CloudFormation stack IDs follow the format:
    arn:aws:cloudformation:region:account-id:stack/stack-name/unique-id
    
    Args:
        stack_id (str): The CloudFormation stack ID/ARN
        
    Returns:
        str: The CloudFormation stack name
        
    Example:
        >>> stack_id = "arn:aws:cloudformation:us-east-1:123456789012:stack/my-stack/abc123"
        >>> name_from_stack_id(stack_id)
        'my-stack'
    """
    return stack_id.split(":")[5].split("/")[1]


def s3_url_maker(bucket, key, s3_client, autobucket=False):
    """
    Generate the correct S3 URL for a given bucket and key.
    
    This function determines the appropriate S3 endpoint URL based on the bucket's
    region and AWS partition. It handles different AWS partitions (standard, China, GovCloud)
    and can optionally wait for bucket creation if autobucket is enabled.
    
    Args:
        bucket (str): The S3 bucket name
        key (str): The S3 object key/path
        s3_client: Boto3 S3 client instance
        autobucket (bool, optional): If True, retry on NoSuchBucket errors.
                                   Defaults to False.
    
    Returns:
        str: The complete S3 URL for the object
        
    Raises:
        TaskCatException: If bucket region cannot be determined
        ClientError: If bucket access is denied and region cannot be discovered
        NoSuchBucket: If bucket doesn't exist and autobucket is False
        
    Example:
        >>> url = s3_url_maker('my-bucket', 'path/to/file.txt', s3_client)
        >>> print(url)
        'https://my-bucket.s3.us-west-2.amazonaws.com/path/to/file.txt'
    """
    retries = 10
    
    while True:
        try:
            try:
                # Try to get bucket location directly
                response = s3_client.get_bucket_location(Bucket=bucket)
                location = response["LocationConstraint"]
            except ClientError as e:
                # If access denied, try to discover region via HTTP headers
                if e.response["Error"]["Code"] != "AccessDenied":
                    raise
                    
                # Make a HEAD request to discover the bucket region
                resp = requests.get(
                    f"https://{bucket}.s3.amazonaws.com/{key}", timeout=3
                )
                location = resp.headers.get("x-amz-bucket-region")
                
                if not location:
                    # pylint: disable=raise-missing-from
                    raise TaskCatException(
                        f"Failed to discover region for bucket {bucket}. "
                        f"Ensure the bucket exists and you have appropriate permissions."
                    )
            break
            
        except s3_client.exceptions.NoSuchBucket:
            # Handle case where bucket doesn't exist yet (for auto-created buckets)
            if not autobucket or retries < 1:
                raise
            retries -= 1
            sleep(5)  # Wait for bucket creation

    # Default case for us-east-1 which returns None as LocationConstraint
    url = f"https://{bucket}.s3.us-east-1.amazonaws.com/{key}"
    
    if location:
        # Get the appropriate domain for the bucket's region/partition
        domain = get_s3_domain(location)
        url = f"https://{bucket}.s3.{location}.{domain}/{key}"
        
    return url


def get_s3_domain(region):
    """
    Get the appropriate S3 domain suffix for a given AWS region.
    
    Different AWS partitions use different domain suffixes for S3 endpoints.
    This function maps regions to their correct domain based on the partition.
    
    Args:
        region (str): AWS region code (e.g., 'us-east-1', 'cn-north-1')
        
    Returns:
        str: The S3 domain suffix for the region's partition
        
    Raises:
        TaskCatException: If the region is not found in the partition mapping
        
    Example:
        >>> get_s3_domain('us-east-1')
        'amazonaws.com'
        >>> get_s3_domain('cn-north-1')
        'amazonaws.com.cn'
    """
    try:
        return S3_PARTITION_MAP[REGIONS[region]]
    except KeyError:
        # pylint: disable=raise-missing-from
        raise TaskCatException(
            f"Cannot find the S3 hostname for region '{region}'. "
            f"This region may not be supported or the region code may be invalid."
        )


def s3_bucket_name_from_url(url):
    """
    Extract the S3 bucket name from an S3 URL.
    
    Args:
        url (str): S3 URL in format https://bucket-name.s3.region.amazonaws.com/key
        
    Returns:
        str: The S3 bucket name
        
    Example:
        >>> s3_bucket_name_from_url('https://my-bucket.s3.us-east-1.amazonaws.com/file.txt')
        'my-bucket'
    """
    return url.split("//")[1].split(".")[0]


def s3_key_from_url(url):
    """
    Extract the S3 object key from an S3 URL.
    
    Args:
        url (str): S3 URL in format https://bucket-name.s3.region.amazonaws.com/key
        
    Returns:
        str: The S3 object key/path
        
    Example:
        >>> s3_key_from_url('https://my-bucket.s3.us-east-1.amazonaws.com/path/to/file.txt')
        'path/to/file.txt'
    """
    return "/".join(url.split("//")[1].split("/")[1:])


class CommonTools:
    """
    Collection of common utility methods for TaskCat operations.
    
    This class provides static utility methods that are used across different
    TaskCat modules for common operations like regex matching and string processing.
    
    Attributes:
        stack_name (str): The CloudFormation stack name associated with this instance
    """
    
    def __init__(self, stack_name):
        """
        Initialize CommonTools with a stack name.
        
        Args:
            stack_name (str): The CloudFormation stack name to associate with this instance
        """
        self.stack_name = stack_name

    @staticmethod
    def regxfind(re_object, data_line):
        """
        Find and return the first regex match in a string.
        
        This method searches for a pattern in the provided string and returns
        the matching substring. If no match is found, it returns 'Not-found'.
        
        Args:
            re_object (re.Pattern): Compiled regular expression object
            data_line (str): String to search for the pattern
            
        Returns:
            str: The matching string if found, otherwise 'Not-found'
            
        Example:
            >>> import re
            >>> pattern = re.compile(r'sg-[a-f0-9]+')
            >>> result = CommonTools.regxfind(pattern, 'SecurityGroup: sg-12345abc')
            >>> print(result)
            'sg-12345abc'
        """
        security_group = re_object.search(data_line)
        if security_group:
            return str(security_group.group())
        return str("Not-found")


def exit_with_code(code, msg=""):
    """
    Exit the application with a specific exit code and optional message.
    
    This function provides a centralized way to exit the application with
    proper logging and exit code handling.
    
    Args:
        code (int): Exit code to return to the operating system
        msg (str, optional): Error message to log before exiting. Defaults to empty string.
    """
    if msg:
        LOG.error(msg)
    sys.exit(code)


def make_dir(path, ignore_exists=True):
    """
    Create a directory and any necessary parent directories.
    
    Args:
        path (str): Path to the directory to create
        ignore_exists (bool, optional): If True, don't raise an error if directory
                                      already exists. Defaults to True.
                                      
    Raises:
        OSError: If directory creation fails or if ignore_exists is False and
                directory already exists
    """
    path = os.path.abspath(path)
    
    # Skip creation if directory exists and ignore_exists is True
    if ignore_exists and os.path.isdir(path):
        return
        
    # Create directory and any necessary parent directories
    os.makedirs(path)


def param_list_to_dict(original_keys):
    """
    Convert a CloudFormation parameter list to a parameter index dictionary.
    
    CloudFormation parameters are often provided as a list of dictionaries with
    'ParameterKey' and 'ParameterValue' keys. This function creates an index
    mapping parameter names to their positions in the list.
    
    Args:
        original_keys (list): List of parameter dictionaries, each containing
                            'ParameterKey' and 'ParameterValue' keys
                            
    Returns:
        dict: Dictionary mapping parameter names to their list indices
        
    Raises:
        TaskCatException: If the input is not a list, if any parameter is not a dict,
                         or if required keys are missing
                         
    Example:
        >>> params = [
        ...     {'ParameterKey': 'VpcId', 'ParameterValue': 'vpc-12345'},
        ...     {'ParameterKey': 'SubnetId', 'ParameterValue': 'subnet-67890'}
        ... ]
        >>> param_list_to_dict(params)
        {'VpcId': 0, 'SubnetId': 1}
    """
    # Setup a list index dictionary for Parameter => Index mapping
    param_index = {}
    
    # Validate input is a list
    if not isinstance(original_keys, list):
        # pylint: disable=raise-missing-from
        raise TaskCatException(
            'Invalid parameter file: outermost JSON element must be a list ("[]")'
        )
    
    # Process each parameter in the list
    for idx, param_dict in enumerate(original_keys):
        # Validate each parameter is a dictionary
        if not isinstance(param_dict, dict):
            # pylint: disable=raise-missing-from
            raise TaskCatException(
                f'Invalid parameter {param_dict}: parameters must be of type dict ("{{}}")'
            )
        
        # Validate required keys are present
        if "ParameterKey" not in param_dict or "ParameterValue" not in param_dict:
            # pylint: disable=raise-missing-from
            raise TaskCatException(
                f"Invalid parameter {param_dict}: all items must "
                f"have both 'ParameterKey' and 'ParameterValue' keys"
            )
        
        # Add parameter to index mapping
        key = param_dict["ParameterKey"]
        param_index[key] = idx
        
    return param_index


def merge_dicts(list_of_dicts):
    """
    Merge multiple dictionaries into a single dictionary.
    
    Later dictionaries in the list will override values from earlier ones
    if there are key conflicts.
    
    Args:
        list_of_dicts (list): List of dictionaries to merge
        
    Returns:
        dict: Merged dictionary containing all key-value pairs
        
    Example:
        >>> dicts = [{'a': 1, 'b': 2}, {'b': 3, 'c': 4}]
        >>> merge_dicts(dicts)
        {'a': 1, 'b': 3, 'c': 4}
    """
    merged_dict = {}
    for single_dict in list_of_dicts:
        merged_dict = {**merged_dict, **single_dict}
    return merged_dict


def pascal_to_snake(pascal):
    """
    Convert PascalCase string to snake_case.
    
    Args:
        pascal (str): String in PascalCase format
        
    Returns:
        str: String converted to snake_case
        
    Example:
        >>> pascal_to_snake('MyVariableName')
        'my_variable_name'
        >>> pascal_to_snake('HTTPSConnection')
        'https_connection'
    """
    # First pass: handle sequences like 'HTTPSConnection' -> 'HTTPS_Connection'
    sub = FIRST_CAP_RE.sub(r"\1_\2", pascal)
    # Second pass: handle remaining cases and convert to lowercase
    return ALL_CAP_RE.sub(r"\1_\2", sub).lower()


def merge_nested_dict(old, new):
    """
    Recursively merge nested dictionaries.
    
    This function performs a deep merge of two dictionaries, where nested
    dictionaries are merged recursively rather than being replaced entirely.
    
    Args:
        old (dict): The base dictionary to merge into (modified in-place)
        new (dict): The dictionary to merge from
        
    Note:
        This function modifies the 'old' dictionary in-place.
        
    Example:
        >>> old = {'a': {'x': 1, 'y': 2}, 'b': 3}
        >>> new = {'a': {'y': 20, 'z': 30}, 'c': 4}
        >>> merge_nested_dict(old, new)
        >>> print(old)
        {'a': {'x': 1, 'y': 20, 'z': 30}, 'b': 3, 'c': 4}
    """
    for k, v in new.items():
        # If both values are dictionaries, merge recursively
        if isinstance(old.get(k), dict) and isinstance(v, collections.abc.Mapping):
            merge_nested_dict(old[k], v)
        else:
            # Otherwise, replace the value
            old[k] = v


def ordered_dump(data, stream=None, dumper=yaml.Dumper, **kwds):
    """
    Dump YAML while preserving the order of OrderedDict objects.
    
    Standard YAML dumping doesn't preserve the order of OrderedDict objects.
    This function creates a custom dumper that maintains the order.
    
    Args:
        data: The data structure to dump to YAML
        stream: Output stream (file-like object) or None for string output
        dumper: YAML dumper class to extend. Defaults to yaml.Dumper
        **kwds: Additional keyword arguments passed to yaml.dump
        
    Returns:
        str or None: YAML string if stream is None, otherwise None
        
    Example:
        >>> from collections import OrderedDict
        >>> data = OrderedDict([('first', 1), ('second', 2)])
        >>> yaml_str = ordered_dump(data)
        >>> print(yaml_str)
        first: 1
        second: 2
    """
    class OrderedDumper(dumper):  # pylint: disable=too-many-ancestors
        """Custom YAML dumper that preserves OrderedDict order."""
        pass

    def _dict_representer(dumper, data):
        """Represent OrderedDict as a regular mapping while preserving order."""
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items()
        )

    # Register the custom representer for OrderedDict
    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def deep_get(dictionary, keys, default=None):
    """
    Get a value from a nested dictionary using a path-like key string.
    
    This function allows accessing nested dictionary values using a slash-separated
    path string, similar to file system paths.
    
    Args:
        dictionary (dict): The dictionary to search in
        keys (str): Slash-separated path to the desired value (e.g., 'level1/level2/key')
        default: Default value to return if the path is not found
        
    Returns:
        The value at the specified path, or the default value if not found
        
    Example:
        >>> data = {'config': {'database': {'host': 'localhost', 'port': 5432}}}
        >>> deep_get(data, 'config/database/host')
        'localhost'
        >>> deep_get(data, 'config/cache/ttl', 300)
        300
    """
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        keys.split("/"),
        dictionary,
    )


def neglect_submodule_templates(project_root, template_list):
    """
    Filter out CloudFormation templates that are located within Git submodules.
    
    This function examines the project's .gitmodules file to identify submodule
    paths and removes any templates that are located within those submodules.
    This prevents TaskCat from processing templates that are part of external
    repositories included as submodules.
    
    Args:
        project_root (Path): Path to the project root directory
        template_list (list): List of template objects to filter
        
    Returns:
        list: Filtered list of template objects excluding those in submodules
        
    Note:
        If no .gitmodules file is found, the original template list is returned unchanged.
    """
    template_dict = {}
    
    # Create a dictionary mapping template paths to template objects
    # Include both main templates and their descendants
    for template in template_list:
        template_dict[template.template_path] = template
        for template_descendent in template.descendents:
            template_dict[template_descendent.template_path] = template_descendent

    # Get submodule path prefixes from .gitmodules
    submodule_path_prefixes = []
    try:
        gitmodule_config = ConfigFile.from_path(Path(project_root / ".gitmodules"))
    except FileNotFoundError:
        # No .gitmodules file found, return original list
        return template_list

    # Parse submodule paths from the configuration
    for submodule_path, _, _ in parse_submodules(gitmodule_config):
        submodule_path_prefixes.append(
            Path(project_root / submodule_path.decode("utf-8"))
        )

    # Filter out templates that are within submodule directories
    finalized_templates = []
    for template_obj in list(template_dict.values()):
        gitmodule_template = False
        
        # Check if this template is within any submodule path
        for gm_path in submodule_path_prefixes:
            if gm_path in template_obj.template_path.parents:
                gitmodule_template = True
                break
                
        # Only include templates that are not in submodules
        if not gitmodule_template:
            finalized_templates.append(template_obj)
            
    return finalized_templates


def determine_profile_for_region(auth_dict, region):
    """
    Determine the appropriate AWS profile to use for a specific region.
    
    This function looks up the AWS profile configuration for a given region,
    falling back to the default profile if no region-specific profile is configured.
    
    Args:
        auth_dict (dict): Dictionary mapping regions to AWS profile names
        region (str): AWS region code to look up
        
    Returns:
        str: AWS profile name to use for the specified region
        
    Example:
        >>> auth_config = {
        ...     'us-east-1': 'prod-profile',
        ...     'us-west-2': 'dev-profile',
        ...     'default': 'default-profile'
        ... }
        >>> determine_profile_for_region(auth_config, 'us-east-1')
        'prod-profile'
        >>> determine_profile_for_region(auth_config, 'eu-west-1')
        'default-profile'
    """
    profile = auth_dict.get(region, auth_dict.get("default", "default"))
    return profile


def fetch_ssm_parameter_value(boto_client, parameter_path):
    """
    Fetch a parameter value from AWS Systems Manager Parameter Store.
    
    Args:
        boto_client: Boto3 client factory function
        parameter_path (str): The parameter path/name in SSM Parameter Store
        
    Returns:
        str: The parameter value from SSM
        
    Raises:
        ClientError: If the parameter doesn't exist or access is denied
        
    Example:
        >>> value = fetch_ssm_parameter_value(boto_client, '/myapp/database/password')
        >>> print(value)
        'secret-password-value'
    """
    ssm = boto_client("ssm")
    response = ssm.get_parameter(Name=parameter_path)
    return response["Parameter"]["Value"]


def fetch_secretsmanager_parameter_value(boto_client, secret_arn):
    """
    Fetch a secret value from AWS Secrets Manager.
    
    Args:
        boto_client: Boto3 client factory function
        secret_arn (str): The ARN or name of the secret in Secrets Manager
        
    Returns:
        str: The secret value from Secrets Manager
        
    Raises:
        TaskCatException: If the secret cannot be retrieved or doesn't exist
        
    Example:
        >>> secret = fetch_secretsmanager_parameter_value(
        ...     boto_client, 
        ...     'arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret-AbCdEf'
        ... )
        >>> print(secret)
        '{"username": "admin", "password": "secret123"}'
    """
    secrets_manager = boto_client("secretsmanager")
    try:
        response = secrets_manager.get_secret_value(SecretId=secret_arn)["SecretString"]
    except Exception as e:
        # pylint: disable=raise-missing-from
        raise TaskCatException(
            f"Failed to retrieve secret from ARN '{secret_arn}': {str(e)}"
        )
    return response
