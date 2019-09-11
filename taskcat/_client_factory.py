import logging
from threading import Lock
from time import sleep

import boto3
import botocore

from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class ClientFactory:
    """Manages creating and caching boto3 clients, helpful when creating lots of
    clients in different regions or functions.

    Example usage:

    from tackcat import utils

    class MyClass(object):
        def __init__(self):
            self._boto_client = utils.ClientFactory()
        def my_function(self):
            s3_client = self._boto_client.get('s3', region='us-west-2')
            return s3_client.list_buckets()
    """

    def __init__(
        self,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        profile_name=None,
        regional_cred_map=None,
    ):
        """Sets up the cache dict, a locking mechanism and the logging object

        Args:
            aws_access_key_id (str): [optional] IAM access key, defaults to None
            aws_secret_access_key (str): [optional] IAM secret key, defaults to None
            aws_session_token (str): [optional] IAM session token, defaults to None
            profile_name (str): [optional] credential profile to use, defaults to None
        """
        regional_cred_map = regional_cred_map if regional_cred_map else {}
        self._clients = {"default": {}}
        self._credential_sets = {}
        self._credential_accounts = {}
        self._credential_instances = {}
        self._lock = Lock()
        self.put_credential_set(
            "default",
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
            profile_name,
        )
        for region_name, credential_dict in regional_cred_map.items():
            self.put_credential_set(region_name, **credential_dict)

    @staticmethod
    def get_default_region(
        aws_access_key_id, aws_secret_access_key, aws_session_token, profile_name
    ):
        """returns the default region for the credentials provided

        :param aws_access_key_id:
        :param aws_secret_access_key:
        :param aws_session_token:
        :param profile_name:
        :return:
        """
        region = "us-east-1"
        try:
            if aws_access_key_id and aws_secret_access_key and aws_session_token:
                session = boto3.session.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token,
                )
            elif aws_access_key_id and aws_secret_access_key:
                session = boto3.session.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
            elif profile_name:
                session = boto3.session.Session(profile_name=profile_name)
            else:
                session = boto3.session.Session()
            region = session.region_name
            if not region:
                LOG.warning(
                    "Region not set in credential chain, defaulting to us-east-1"
                )
                region = "us-east-1"
        except Exception as e:  # pylint: disable=broad-except
            LOG.error("failed to get default region: %s" % str(e))
        return region

    def put_credential_set(
        self,
        credential_set_name,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        profile_name=None,
    ):
        """Adds or updates a credential set to be re-used when creating clients

            aws_access_key_id (str): [optional] IAM access key, defaults to None
            aws_secret_access_key (str): [optional] IAM secret key, defaults to None
            aws_session_token (str): [optional] IAM session token, defaults to None
            profile_name (str): [optional] credential profile to use, defaults to None
        """
        if (aws_access_key_id and not aws_secret_access_key) or (
            not aws_access_key_id and aws_secret_access_key
        ):
            raise ValueError(
                '"aws_access_key_id" and "aws_secret_access_key" must both be set'
            )
        if profile_name and (
            aws_access_key_id or aws_secret_access_key or aws_session_token
        ):
            raise ValueError(
                '"profile_name" cannot be used with aws_access_key_id, aws_secret_'
                "access_key or aws_session_token"
            )
        self._credential_sets[credential_set_name] = [
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
            profile_name,
        ]
        self._credential_sets[credential_set_name] = [
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
            profile_name,
        ]

    # TODO: reduce complexity in method
    def get(  # noqa: C901
        self,
        service,
        region=None,
        credential_set="default",
        key=None,
        secret=None,
        token=None,
        s3v4=False,
        profile=None,
    ):
        """get a client for a given service and region, optionally with specific role,
        credentials and/or sig version

        Args:
            service (str): service name
            region (str): [optional] region name, defaults to current region
            credential_set (str): [optional] name used to seperate different sets of
                credentials, defaults to "default" which uses either the auto-discovered
                role, or the credentials configured when this class is instantiated
            key (str): [optional] IAM access key, defaults to None
            secret (str): [optional] IAM secret key, defaults to None
            token (str): [optional] IAM session token, defaults to None
            s3v4 (bool): [optional] when True enables signature_version=s3v4 which is
                required for SSE protected buckets/objects
            profile (str): [optional] credential profile to use, defaults to None
        Returns:
            class: boto3 client
        """
        if not key and not profile:
            LOG.debug(
                f"no explicit keys or profile for this client, fetching the "
                f"credentials from the {credential_set} set"
            )
            if credential_set not in self._credential_sets.keys():
                raise KeyError("credential set %s does not exist" % credential_set)
            if region and region in self._credential_sets.keys():
                credential_set = region
            key, secret, token, profile = self._credential_sets[credential_set]
        if not region:
            region = self.get_default_region(key, secret, token, profile)

        s3v4 = "s3v4" if s3v4 else "default_sig_version"
        try:
            LOG.debug(
                "Trying to get [%s][%s][%s][%s]"
                % (credential_set, region, service, s3v4)
            )
            client = self._clients[credential_set][region][service][s3v4]
            if key:
                if (
                    self._clients[credential_set][region]["session"]
                    .get_credentials()
                    .access_key
                    != key
                ):
                    LOG.debug("credentials changed, forcing update...")
                    raise KeyError(
                        "New credentials for this credential_set, need a new session."
                    )
            return client
        except KeyError:
            LOG.debug("Couldn't return an existing client, making a new one...")
            if credential_set not in self._clients.keys():
                self._clients[credential_set] = {}
            if region not in self._clients[credential_set].keys():
                self._clients[credential_set][region] = {}
            if service not in self._clients[credential_set].keys():
                self._clients[credential_set][region][service] = {}
            if "session" not in self._clients[credential_set][region].keys():
                self._clients[credential_set][region]["session"] = self._create_session(
                    region, key, secret, token, profile
                )
            self._clients[credential_set][region][service][s3v4] = self.create_client(
                credential_set, region, service, s3v4
            )
            client = self._clients[credential_set][region][service][s3v4]

        client.clientfactory_credset_name = credential_set
        return client

    def _create_session(
        self,
        region,
        access_key=None,
        secret_key=None,
        session_token=None,
        profile_name=None,
        max_retries=4,
        delay=5,
        backoff_factor=2,
    ):
        """creates a boto3 session object

        Args:
            region (str): region name
            access_key (str): [optional] IAM secret key, defaults to None
            secret_key (str): [optional] IAM secret key, defaults to None
            session_token (str): [optional] IAM secret key, defaults to None
            profile_name (str): [optional] credential profile to use, defaults to None
            max_retries (int): [optional] number of retries, defaults to 4
            delay (int): [optional] retry delay in seconds, defaults to 5
            backoff_factor (int): [optional] retry delay exponent, defaults to 2
        """
        session = None
        retry = 0
        while not session:
            try:
                with self._lock:
                    if access_key and secret_key and session_token:
                        session = boto3.session.Session(
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key,
                            aws_session_token=session_token,
                            region_name=region,
                        )
                    elif access_key and secret_key:
                        session = boto3.session.Session(
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key,
                            region_name=region,
                        )
                    elif profile_name:
                        session = boto3.session.Session(
                            profile_name=profile_name, region_name=region
                        )
                    else:
                        session = boto3.session.Session(region_name=region)
                return session
            except TaskCatException:
                raise
            except Exception as e:  # pylint: disable=broad-except
                if "could not be found" in str(e):
                    raise
                LOG.debug("failed to create session", exc_info=1)
                retry += 1
                if retry >= max_retries:
                    raise
                sleep(delay * (retry ** backoff_factor))

    def create_client(
        self,
        credential_set: str,
        region: str,
        service: str,
        s3v4="s3v4",
        max_retries=4,
        delay=5,
        backoff_factor=2,
    ):
        """creates (or fetches from cache) a boto3 client object

        Args:
            credential_set (str): session name
            region (str): region name
            service (str): AWS service name
            s3v4 (str): when set to "s3v4" enables signature version 4, required for
                SSE protected buckets/objects
            max_retries (int): [optional] number of retries, defaults to 4
            delay (int): [optional] retry delay in seconds, defaults to 5
            backoff_factor (int): [optional] retry delay exponent, defaults to 2
        """
        client = None
        retry = 0
        while not client:
            try:
                with self._lock:
                    if s3v4 == "s3v4":
                        client = self._clients[credential_set][region][
                            "session"
                        ].client(
                            service,
                            config=botocore.client.Config(signature_version="s3v4"),
                        )
                    else:
                        client = self._clients[credential_set][region][
                            "session"
                        ].client(service)
                return client
            except TaskCatException:
                raise
            except Exception:  # pylint: disable=broad-except
                LOG.debug("failed to create client", exc_info=True)
                retry += 1
                if retry >= max_retries:
                    raise
                sleep(delay * (retry ** backoff_factor))

    def credset_exists(self, credset_name) -> bool:
        """
        Asserts that a particular credset exists within the instance.

        Args:
            credset_name (str): Credential Set Name

        Returns:
            bool
        :param credset_name:
        :return:
        """
        if credset_name in self._credential_sets.keys():
            return True
        return False

    def get_available_regions(self, service):
        """fetches available regions for a service

        Args:
            service (str): AWS service name

        Returns:
            list: aws region name strings
        """

        for credential_set in self._clients:
            for region in self._clients[credential_set].keys():
                if "session" in self._clients[credential_set][region].keys():
                    return self._clients[credential_set][region][
                        "session"
                    ].get_available_regions(service)
        session = boto3.session.Session()
        return session.get_available_regions(service)

    def get_session(self, credential_set, region=None):
        """fetches existing session for credential set in a region

        Args:
            credential_set (str): name of credential set from a previously created
                client
            region (str): region name, defaults to current region

        Returns:
            boto3.session.Session: instance of boto3 Session object
        """
        if not region:
            creds = self._credential_sets[credential_set]
            region = self.get_default_region(*creds)
        if not self._clients[credential_set].get(region):
            creds = self._credential_sets[credential_set]
            self._clients[credential_set][region] = {
                "session": self._create_session(region, *creds)
            }

        return self._clients[credential_set][region]["session"]

    def return_credset_instance(self, credential_set_name):
        """
        Returns a ClientFactory instance, given a credential_set_name.
        The credentials configured under the credential_set_name are set to 'default'
        in the returned instance.

        Args:
            credential_set_name (str): credential set name to return.
        Returns:
            ClientFactory: instance of ClientFactory using
                creds from the Credential Set Name
            or None
        """
        if credential_set_name == "default":
            return self
        cached_instance = self._credential_instances.get(credential_set_name, None)
        if cached_instance:
            return cached_instance
        if credential_set_name in self._credential_sets.keys():
            cf_creds = self._credential_sets[credential_set_name]
            cf_instance = ClientFactory(*cf_creds)
            self._credential_instances[credential_set_name] = cf_instance
            return cf_instance
        return None
