#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function

import boto3
import botocore
import unittest
import logging
from threading import Lock
import mock
import os
from taskcat.client_factory import ClientFactory


class MockClientConfig(object):
    def __init__(self):
        self.region_name = "us-east-2"


class MockBotoClient(object):
    def __init__(self):
        self.session = MockBotoSession()
        pass

    def client(self, service, region_name=None, access_key=None, secret_key=None, session_token=None, s3v4=True):
        return MockClient()


class MockBotoSession(object):
    def __init__(self):
        pass


class MockBotoSessionClass(object):
    def __init__(self):
        pass

    def get_available_regions(self, *args, **kwargs):
        return ['us-east-1']

    def client(self, service, config=None):
        return MockBotoClient().client(service)

    def get_credentials(self):
        return MockCredentials()


class MockCredentials(object):
    def __init__(self):
        self.access_key = "some-key"


class MockClient(object):
    def __init__(self):
        self._client_config = MockClientConfig()
        pass


def client_factory_instance():
    with mock.patch.object(ClientFactory, '__init__', return_value=None):
        aws_clients = ClientFactory(None)
    aws_clients._credential_sets = {'default': [None, None, None, None]}
    aws_clients.logger = logging.getLogger()
    aws_clients._clients = {"default": {}}
    aws_clients._lock = Lock()
    return aws_clients


class TestClientFactory(unittest.TestCase):
    def test___init__(self):
        # Mock the put_credential_set method that is called during init
        with mock.patch.object(ClientFactory, 'put_credential_set', return_value=None):
            aws_clients = ClientFactory(None)

            msg = "clients should be empty"
            self.assertEqual({"default": {}}, aws_clients._clients, msg)

            msg = "lock should be an instance of Lock"
            self.assertEqual(type(Lock()), type(aws_clients._lock), msg)

            msg = "logger should exist and level set to ERROR"
            logger = logging.getLogger()
            logger.setLevel(logging.ERROR)
            self.assertEqual(logger, aws_clients.logger, msg)

            msg = "logger should exist and level set to WARNING"
            logger.setLevel(logging.WARNING)
            aws_clients = ClientFactory(logger)
            self.assertEqual(logger, aws_clients.logger, msg)

    def test_put_credential_set(self):
        aws_clients = client_factory_instance()

        msg = "should not raise an exception when optional parameters are not passed"
        self.assertEqual(aws_clients.put_credential_set("default"), None, msg)

        msg = "should raise ValueError for missing keyid or secret"
        exception_message = '"aws_access_key_id" and "aws_secret_access_key" must both be set'
        with self.assertRaises(ValueError) as e:
            aws_clients.put_credential_set("default", aws_access_key_id="test")
        self.assertEqual(str(e.exception), exception_message, msg)
        with self.assertRaises(ValueError) as e:
            aws_clients.put_credential_set("default", aws_secret_access_key="test")
        self.assertEqual(str(e.exception), exception_message, msg)

        msg = "should raise ValueError for missing keyid or secret"
        exception_message = '"profile_name" cannot be used with aws_access_key_id, aws_secret_access_key or aws_session_token'
        with self.assertRaises(ValueError) as e:
            aws_clients.put_credential_set("default", profile_name="test", aws_access_key_id="test", aws_secret_access_key="test")
        self.assertEqual(str(e.exception), exception_message, msg)
        with self.assertRaises(ValueError) as e:
            aws_clients.put_credential_set("default", profile_name="test", aws_session_token="test")
        self.assertEqual(str(e.exception), exception_message, msg)

        msg = "should set default credentials with empty creds in _credential_sets"
        aws_clients._credential_sets = {}
        aws_clients.put_credential_set("default")
        self.assertEqual({'default': [None, None, None, None]}, aws_clients._credential_sets, msg)

        msg = "should set test credentials with key, secret and token in _credential_sets"
        aws_clients._credential_sets = {}
        aws_clients.put_credential_set("test", aws_access_key_id="test", aws_secret_access_key="test", aws_session_token="test")
        self.assertEqual({'test': ["test", "test", "test", None]}, aws_clients._credential_sets, msg)

        msg = "should set test credentials with profile in _credential_sets"
        aws_clients._credential_sets = {}
        aws_clients.put_credential_set("test", profile_name="test")
        self.assertEqual({'test': [None, None, None, "test"]}, aws_clients._credential_sets, msg)

        msg = "should replace test set in _credential_sets"
        aws_clients.put_credential_set("test")
        self.assertEqual({'test': [None, None, None, None]}, aws_clients._credential_sets, msg)

        msg = "should add to existing set in _credential_sets"
        aws_clients.put_credential_set("test2")
        expected = {'test': [None, None, None, None], 'test2': [None, None, None, None]}
        self.assertEqual(expected, aws_clients._credential_sets, msg)

    @mock.patch("taskcat.ClientFactory._create_client", mock.MagicMock(return_value=MockClient()))
    @mock.patch("taskcat.ClientFactory._create_session", mock.MagicMock(return_value=MockBotoSessionClass()))
    def test_get(self):
        aws_clients = client_factory_instance()
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

        msg = "should add additional key if profile/key is provided and credential set does not exist"
        aws_clients.get("test_service", profile_name="test", credential_set="nonexistant")
        self.assertIn("nonexistant", aws_clients._clients.keys(), msg)

        ClientFactory._create_client.reset_mock()
        msg = "should raise KeyError if credential set provided does not exist"
        exception_message = "'credential set nonexistant does not exist'"
        with self.assertRaises(KeyError) as e:
            aws_clients.get("test", credential_set='nonexistant')
        self.assertEqual(exception_message, str(e.exception), msg)

        msg = "should return a client instance"
        client = aws_clients.get("test_service")
        self.assertEqual(MockClient, type(client), msg)

        msg = "'default' cache key should contain region key"
        self.assertEqual(["us-east-1"], list(aws_clients._clients["default"].keys()), msg)

        msg = "region cache entry should contain service name key"
        self.assertIn("test_service", list(aws_clients._clients["default"]['us-east-1'].keys()), msg)

        msg = "region cache entry should contain session key"
        self.assertIn("session", list(aws_clients._clients["default"]['us-east-1'].keys()), msg)

        msg = "session should be an instance of boto session"
        self.assertEqual(MockBotoSessionClass, type(aws_clients._clients["default"]['us-east-1']['session']), msg)
        msg = "service cache entry should contain default sig key"
        self.assertEqual(["default_sig_version"], list(aws_clients._clients["default"]['us-east-1']["test_service"].keys()), msg)

        msg = "client should be added to cache"
        self.assertEqual(client, aws_clients._clients["default"]['us-east-1']["test_service"]['default_sig_version'], msg)

        ClientFactory._create_client.assert_called_once()

        # should return a new client instance if credentials for an existing session have changed
        ClientFactory._create_client.reset_mock()
        aws_clients.get("test_service", aws_access_key_id="test")
        ClientFactory._create_client.assert_called_once()

        # should use cached client if one exists
        aws_clients.get("test_service")
        ClientFactory._create_client.assert_called_once()


    def test__create_session(self):
        aws_clients = client_factory_instance()
        with mock.patch.object(boto3, 'session', return_value=MockBotoSession()):
            aws_clients._create_session('us-east-2')

            # check that session is created with correct region
            boto3.session.Session.assert_called_once_with(region_name='us-east-2')

            # check that session is created with provided creds
            boto3.session.Session.reset_mock()
            aws_clients._create_session('us-east-2', access_key="test_key", secret_key="test_secret", session_token="test_token")
            boto3.session.Session.assert_called_once_with(region_name='us-east-2', aws_access_key_id='test_key', aws_secret_access_key='test_secret', aws_session_token='test_token')
            boto3.session.Session.reset_mock()
            aws_clients._create_session('us-east-2', access_key="test_key", secret_key="test_secret")
            boto3.session.Session.assert_called_once_with(region_name='us-east-2', aws_access_key_id='test_key',
                                                          aws_secret_access_key='test_secret')
            boto3.session.Session.reset_mock()
            aws_clients._create_session('us-east-2', profile_name="test_profile")
            boto3.session.Session.assert_called_once_with(region_name='us-east-2', profile_name="test_profile")

            # should fail without retries on permanent error "could not be found"
            boto3.session.Session.reset_mock()
            boto3.session.Session.side_effect = Exception("could not be found")
            with self.assertRaises(Exception) as e:
                aws_clients._create_session('us-east-2')
            boto3.session.Session.assert_called_once()

            # Mock boto3 session to fail on 1st invocation
            msg = "should not raise on intermittent exceptions"
            boto3.session.Session.reset_mock()
            boto3.session.Session.side_effect = [KeyError("test_failure"), MockBotoSession()]
            aws_clients._create_session('us-east-2', delay=1, backoff_factor=1)
            self.assertEqual(2, boto3.session.Session.call_count, msg)

            # Mock boto3 to fail permanently
            boto3.session.Session.side_effect = KeyError("test_failure")
            msg = "should retry call 5 times and then raise exception"
            with self.assertRaises(KeyError) as e:
                aws_clients._create_session('us-east-2', delay=1, backoff_factor=1)
            self.assertEqual(6, boto3.session.Session.call_count, msg)

    @mock.patch("botocore.client.Config", mock.MagicMock(return_value=None))
    def test__create_client(self):
        aws_clients = client_factory_instance()
        aws_clients._clients["default"] = {"us-east-1": {"session": MockBotoSessionClass()}}

        msg = "should return a boto3 client"
        client = aws_clients._create_client("default", "us-east-1", "test_service", False, delay=1, backoff_factor=1)
        self.assertEqual(MockClient, type(client), msg)

        msg = "should create a sig v4 client"
        botocore.client.Config.reset_mock()
        client = aws_clients._create_client("default", "us-east-1", "test_service", "s3v4", delay=1, backoff_factor=1)
        botocore.client.Config.assert_called_once_with(signature_version='s3v4')
        self.assertEqual(MockClient, type(client), msg)

        msg = "if boto3 fails, should retry 4 times before raising"
        botocore.client.Config.reset_mock()
        botocore.client.Config.side_effect = KeyError("test_failure")
        with self.assertRaises(KeyError) as e:
            aws_clients._create_client("default", "us-east-1", "test_service", "s3v4", delay=1, backoff_factor=1)
        self.assertEqual(4, botocore.client.Config.call_count, msg)

        msg = "should not raise on intermittent exceptions"
        botocore.client.Config.reset_mock()
        botocore.client.Config.side_effect = [KeyError("test_failure"), MockBotoSession()]
        client = aws_clients._create_client("default", "us-east-1", "test_service", "s3v4", delay=1, backoff_factor=1)
        self.assertEqual(2, botocore.client.Config.call_count, msg)
        self.assertEqual(MockClient, type(client), msg)

    def test_get_available_regions(self):
        aws_clients = client_factory_instance()
        aws_clients._clients["default"] = {"us-east-1": {"session": MockBotoSessionClass()}}

        msg = "should return a list of strings"
        regions = aws_clients.get_available_regions("test_service")
        self.assertEqual(["us-east-1"], regions, msg)

        msg = "if there are existing sessions, should use one of them"
        mock_session = mock.MagicMock(return_value=MockBotoSessionClass())
        aws_clients._clients["default"] = {"us-east-1": {"session": mock_session}}
        aws_clients.get_available_regions("test_service")
        self.assertEqual(1, mock_session.get_available_regions.call_count, msg)

        msg = "if there are no existing sessions, should create a new one"
        mock_session.get_available_regions.reset_mock()
        aws_clients._clients["default"] = {"us-east-1": {}}
        with mock.patch.object(boto3, 'session', return_value=MockBotoSession()):
            aws_clients.get_available_regions("test_service")
            boto3.session.Session.assert_called_once()
        self.assertEqual(0, mock_session.get_available_regions.call_count, msg)

    def test_get_session(self):
        aws_clients = client_factory_instance()
        ue1_session = MockBotoSessionClass()
        ue2_session = MockBotoSessionClass()
        aws_clients._clients["default"] = {
            "us-east-1": {"session": ue1_session},
            "us-east-2": {"session": ue2_session}
        }

        msg = "if region not provided, should be fetched from env var"
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        s = aws_clients.get_session("default")
        self.assertEqual(ue1_session, s, msg)

        msg = "if region provided, should be used to fetch session"
        s = aws_clients.get_session("default", "us-east-2")
        self.assertEqual(ue2_session, s, msg)


if __name__ == '__main__':
    unittest.main()
