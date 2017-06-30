import boto3
import botocore
import logging
import os
from threading import Lock
from time import sleep


class ClientFactory(object):

    """Manages creating and caching boto3 clients"""

    def __init__(self, logger=None):
        """Sets up the cache dict, a locking mechanism and the logging object

        Args:
            logger (obj): a logging instance
        """

        self._clients = {"default_role": {}}
        self._lock = Lock()
        if not logger:
            loglevel = getattr(logging, 'ERROR', 20)
            botolevel = getattr(logging, 'ERROR', 40)
            self.logger = logging.getLogger()
            self.logger.addHandler(logging.StreamHandler())
            self.logger.setLevel(loglevel)
            logging.getLogger('boto3').setLevel(botolevel)
            logging.getLogger('botocore').setLevel(botolevel)
            logging.getLogger('nose').setLevel(botolevel)
            logging.getLogger('s3transfer').setLevel(botolevel)
        else:
            self.logger = logger
        return

    def get(self, service, region=None, role='default_role', access_key=None, secret_key=None,
            session_token=None, s3v4=False):
        """get a client for a given service and region, optionally with specific role, credentials and/or sig version

        Args:
            service (str): service name
            region (str): [optional] region name, defaults to current region
            role (str): [optional] descriptive role name used to seperate different sets of credentials for the same service/region, defaults to default_role which uses the lambda execution role
            access_key (str): [optional] IAM access key, defaults to None (uses execution role creds)
            secret_key (str): [optional] IAM secret key, defaults to None (uses execution role creds)
            session_token (str): [optional] IAM session token, defaults to None (uses execution role creds)
            s3v4 (bool): [optional] when True enables signature_version=s3v4 which is required for SSE protected buckets/objects

        Returns:
            class: boto3 client
        """

        if not region:
            self.logger.debug("Region not set explicitly, getting default region")
            region = os.environ['AWS_DEFAULT_REGION']
        s3v4 = 's3v4' if s3v4 else 'default_sig_version'
        try:
            self.logger.debug("Trying to get [%s][%s][%s][%s]" % (role, region, service, s3v4))
            client = self._clients[role][region][service][s3v4]
            if access_key:
                if self._clients[role][region]['session'].get_credentials().access_key != access_key:
                    self.logger.debug("credentials changed, forcing update...")
                    raise KeyError("New credentials for this role, need a new session.")
            return client
        except KeyError:
            self.logger.debug("Couldn't return an existing client, making a new one...")
            if role not in self._clients.keys():
                self._clients[role] = {}
            if region not in self._clients[role].keys():
                self._clients[role][region] = {}
            if service not in self._clients[role].keys():
                self._clients[role][region][service] = {}
            if 'session' not in self._clients[role][region].keys():
                self._clients[role][region]['session'] = self._create_session(region, access_key, secret_key,
                                                                              session_token)
            self._clients[role][region][service][s3v4] = self._create_client(role, region, service, s3v4)
            return self._clients[role][region][service][s3v4]

    def _create_session(self, region, access_key, secret_key, session_token):
        """creates (or fetches from cache) a boto3 session object

        Args:
            region (str): region name
            access_key (str): [optional] IAM secret key, defaults to None (uses execution role creds)
            secret_key (str): [optional] IAM secret key, defaults to None (uses execution role creds)
            session_token (str): [optional] IAM secret key, defaults to None (uses execution role creds)
        """
        session = None
        retry = 0
        max_retries = 4
        while not session:
            try:
                with self._lock:
                    if access_key and secret_key and session_token:
                        session = boto3.session.Session(
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key,
                            aws_session_token=session_token,
                            region_name=region
                        )
                    else:
                        session = boto3.session.Session(region_name=region)
                return session
            except Exception:
                self.logger.debug("failed to create session", exc_info=1)
                retry += 1
                if retry >= max_retries:
                    raise
                sleep(5*(retry**2))

    def _create_client(self, role, region, service, s3v4):
        """creates (or fetches from cache) a boto3 client object

        Args:
            role (str): role descriptor
            region (str): region name
            service (str): AWS service name
            s3v4 (bool): when True enables signature_version=s3v4 which is required for SSE protected buckets/objects
        """
        client = None
        retry = 0
        max_retries = 4
        while not client:
            try:
                with self._lock:
                    if s3v4 == 's3v4':
                        client = self._clients[role][region]['session'].client(
                            service,
                            config=botocore.client.Config(signature_version='s3v4')
                        )
                    else:
                        client = self._clients[role][region]['session'].client(service)
                return client
            except Exception:
                self.logger.debug("failed to create client", exc_info=1)
                retry += 1
                if retry >= max_retries:
                    raise
                sleep(5*(retry**2))

    def get_available_regions(self, service):
        """fetches available regions for a service

        Args:
            service (str): AWS service name

        Returns:
            list: aws region name strings
        """

        for role in self._clients.keys():
            for region in self._clients[role].keys():
                if 'session' in self._clients[role][region].keys():
                    return self._clients[role][region]['session'].get_available_regions(service)
        session = boto3.session.Session()
        return session.get_available_regions(service)
