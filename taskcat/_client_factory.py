import logging
import operator
from functools import reduce
from time import sleep
from typing import Any, Dict, List

import boto3
import botocore.loaders as boto_loader
import botocore.regions as boto_regions
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)

REGIONAL_ENDPOINT_SERVICES = ["sts"]


class Boto3Cache:
    RETRIES = 10
    BACKOFF = 2
    DELAY = 0.1
    CLIENT_THROTTLE_RETRIES = 20

    def __init__(self, _boto3=boto3):
        self._boto3 = _boto3
        self._session_cache: Dict[str, Dict[str, boto3.Session]] = {}
        self._client_cache: Dict[str, Dict[str, Dict[str, boto3.client]]] = {}
        self._resource_cache: Dict[str, Dict[str, Dict[str, boto3.resource]]] = {}
        self._account_info: Dict[str, Dict[str, str]] = {}
        self._lock_cache_update = False

    def session(self, profile: str = "default", region: str = None) -> boto3.Session:
        region = self._get_region(region, profile)
        try:
            session = self._cache_lookup(
                self._session_cache,
                [profile, region],
                self._boto3.Session,
                [],
                {"region_name": region, "profile_name": profile},
            )
        except ProfileNotFound:
            if profile != "default":
                raise
            session = self._boto3.Session(region_name=region)
            self._cache_set(self._session_cache, [profile, region], session)
        return session

    def client(
        self, service: str, profile: str = "default", region: str = None
    ) -> boto3.client:
        region = self._get_region(region, profile)
        session = self.session(profile, region)
        kwargs = {"config": BotoConfig(retries={"max_attempts": 20})}
        if service in REGIONAL_ENDPOINT_SERVICES:
            kwargs.update({"endpoint_url": self._get_endpoint_url(service, region)})
        return self._cache_lookup(
            self._client_cache,
            [profile, region, service],
            session.client,
            [service],
            kwargs,
        )

    def resource(
        self, service: str, profile: str = "default", region: str = None
    ) -> boto3.resource:
        region = self._get_region(region, profile)
        session = self.session(profile, region)
        return self._cache_lookup(
            self._resource_cache,
            [profile, region, service],
            session.resource,
            [service],
        )

    def partition(self, profile: str = "default") -> str:
        return self._cache_lookup(
            self._account_info, [profile], self._get_account_info, [profile]
        )["partition"]

    def account_id(self, profile: str = "default") -> str:
        return self._cache_lookup(
            self._account_info, [profile], self._get_account_info, [profile]
        )["account_id"]

    def _get_account_info(self, profile):
        partition, region = self._get_partition(profile)
        session = self.session(profile, region)
        sts_client = session.client("sts", region_name=region)
        try:
            account_id = sts_client.get_caller_identity()["Account"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "AccessDenied":
                # pylint: disable=raise-missing-from
                raise TaskCatException(
                    f"Not able to fetch account number from {region} using profile "
                    f"{profile}. {str(e)}"
                )
            raise
        except NoCredentialsError as e:
            # pylint: disable=raise-missing-from
            raise TaskCatException(
                f"Not able to fetch account number from {region} using profile "
                f"{profile}. {str(e)}"
            )
        except ProfileNotFound as e:
            # pylint: disable=raise-missing-from
            raise TaskCatException(
                f"Not able to fetch account number from {region} using profile "
                f"{profile}. {str(e)}"
            )
        return {"partition": partition, "account_id": account_id}

    def _make_parent_keys(self, cache: dict, keys: list):
        if keys:
            if not cache.get(keys[0]):
                cache[keys[0]] = {}
            self._make_parent_keys(cache[keys[0]], keys[1:])

    def _cache_lookup(self, cache, key_list, create_func, args=None, kwargs=None):
        try:
            value = self._cache_get(cache, key_list)
        except KeyError:
            args = [] if not args else args
            kwargs = {} if not kwargs else kwargs
            value = self._get_with_retry(create_func, args, kwargs)
            self._cache_set(cache, key_list, value)
        return value

    def _get_with_retry(self, create_func, args, kwargs):
        retries = self.RETRIES
        delay = self.DELAY
        while retries:
            try:
                return create_func(*args, **kwargs)
            except KeyError as e:
                if str(e) not in ["'credential_provider'", "'endpoint_resolver'"]:
                    raise
                backoff = (self.RETRIES - retries + delay) * self.BACKOFF
                sleep(backoff)

    @staticmethod
    def _get_endpoint_url(service, region):
        data = boto_loader.create_loader().load_data("endpoints")
        endpoint_data = boto_regions.EndpointResolver(data).construct_endpoint(
            service, region
        )
        if not endpoint_data:
            raise TaskCatException(
                f"unable to resolve endpoint for {service} in {region}"
            )
        return f"https://{service}.{region}.{endpoint_data['dnsSuffix']}"

    @staticmethod
    def _cache_get(cache: dict, key_list: List[str]):
        return reduce(operator.getitem, key_list, cache)

    def _cache_set(self, cache: dict, key_list: list, value: Any):
        self._make_parent_keys(cache, key_list[:-1])
        self._cache_get(cache, key_list[:-1])[key_list[-1]] = value

    def _get_region(self, region, profile):
        if not region:
            region = self.get_default_region(profile)
        return region

    def _get_partition(self, profile):
        partition_regions = [
            ("aws", "us-east-1"),
            ("aws-cn", "cn-north-1"),
            ("aws-us-gov", "us-gov-west-1"),
        ]
        for partition, region in partition_regions:
            try:
                self.session(profile, region).client(
                    "sts", region_name=region
                ).get_caller_identity()
                return (partition, region)
            except ClientError as e:
                if "InvalidClientTokenId" in str(e):
                    continue
                raise
        raise ValueError("cannot find suitable AWS partition")

    def get_default_region(self, profile_name="default") -> str:
        try:
            region = self._boto3.session.Session(profile_name=profile_name).region_name
        except ProfileNotFound:
            if profile_name != "default":
                raise
            region = self._boto3.session.Session().region_name
        if not region:
            _, region = self._get_partition(profile_name)
            LOG.warning(
                "Region not set in credential chain, defaulting to {}".format(region)
            )
        return region
