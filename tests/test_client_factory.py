import unittest
from unittest import mock

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from taskcat._client_factory import Boto3Cache
from taskcat.exceptions import TaskCatException


class TestBoto3Cache(unittest.TestCase):
    @mock.patch("taskcat._client_factory.boto3", autospec=True)
    def test_stable_concurrency(self, mock_boto3):
        # Sometimes boto fails with KeyErrors under high concurrency
        for key_error in ["endpoint_resolver", "credential_provider"]:
            mock_boto3.Session.side_effect = [KeyError(key_error), mock.DEFAULT]
            c = Boto3Cache(_boto3=mock_boto3)
            c.session("default")

    @mock.patch("taskcat._client_factory.Boto3Cache._cache_set", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache._cache_lookup", autospec=True)
    def test_session_invalid_profile(self, mock_cache_lookup, mock_cache_set):
        mock_cache_lookup.side_effect = ProfileNotFound(profile="non-existent-profile")
        cache = Boto3Cache()
        with self.assertRaises(ProfileNotFound):
            cache.session(profile="non-existent-profile")
        self.assertEqual(mock_cache_lookup.called, False)
        cache._get_region = mock.Mock(return_value="us-east-1")
        with self.assertRaises(ProfileNotFound):
            cache.session(profile="non-existent-profile")
        self.assertEqual(mock_cache_lookup.called, True)

    @mock.patch("taskcat._client_factory.Boto3Cache._get_partition", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache._cache_set", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache._cache_lookup", autospec=True)
    @mock.patch("taskcat._client_factory.boto3.Session", autospec=True)
    def test_session_no_profile(
        self, mock_boto3, mock_cache_lookup, mock_cache_set, mock_get_partition
    ):
        mock_get_partition.return_value = (None, "us-east-1")
        mock_cache_lookup.side_effect = ProfileNotFound(profile="non-existent-profile")
        Boto3Cache().session()  # default value should be "default" profile
        self.assertEqual(mock_boto3.called, True)
        self.assertEqual(mock_cache_lookup.called, True)
        self.assertEqual(mock_cache_set.called, True)

    @mock.patch("taskcat._client_factory.Boto3Cache._get_region", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache._cache_lookup", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache.session", autospec=True)
    def test_client(self, mock_session, mock_cache_lookup, mock__get_region):
        Boto3Cache().client("s3")
        self.assertEqual(mock_session.called, True)
        self.assertEqual(mock_cache_lookup.called, True)
        self.assertEqual(mock__get_region.called, True)

    @mock.patch("taskcat._client_factory.Boto3Cache._get_endpoint_url")
    @mock.patch("taskcat._client_factory.Boto3Cache._get_region", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache._cache_lookup", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache.session", autospec=True)
    def test_client_sts(
        self, mock_session, mock_cache_lookup, mock__get_region, mock__get_endpoint_url
    ):
        mock__get_endpoint_url.return_value = "https://sts.us-east-1.amazonaws.com"
        Boto3Cache().client("sts")
        self.assertEqual(mock_session.called, True)
        self.assertEqual(mock_cache_lookup.called, True)
        self.assertEqual(mock__get_region.called, True)
        self.assertEqual(mock__get_endpoint_url.called, True)

    @mock.patch("taskcat._client_factory.Boto3Cache._get_region", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache._cache_lookup", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache.session", autospec=True)
    def test_resource(self, mock_session, mock_cache_lookup, mock__get_region):
        Boto3Cache().resource("s3")
        self.assertEqual(mock_session.called, True)
        self.assertEqual(mock_cache_lookup.called, True)
        self.assertEqual(mock__get_region.called, True)

    @mock.patch("taskcat._client_factory.Boto3Cache._cache_lookup", autospec=True)
    def test_partition(self, mock_cache_lookup):
        Boto3Cache().partition()
        self.assertEqual(mock_cache_lookup.called, True)

    @mock.patch("taskcat._client_factory.Boto3Cache._cache_lookup", autospec=True)
    def test_account_id(self, mock_cache_lookup):
        Boto3Cache().account_id()
        self.assertEqual(mock_cache_lookup.called, True)

    @mock.patch("taskcat._client_factory.boto3", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache._get_partition", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache._get_region", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache.session")
    def test__get_account_info(
        self, mock_session, mock__get_region, mock__get_partition, mock_boto3
    ):
        mock__get_region.return_value = "us-east-1"
        session = boto3.Session()
        session.get_available_regions = mock.Mock()
        session.client = mock.Mock()
        sts = mock.Mock()
        sts.get_caller_identity.return_value = {"Account": "123412341234"}
        session.client.return_value = sts
        mock_session.return_value = session
        mock_boto3.session.Session = mock.Mock()
        mock_boto3.session.Session.return_value = session
        cache = Boto3Cache(_boto3=mock_boto3)

        mock__get_partition.return_value = ("aws-us-gov", "us-gov-east-1")
        partition = cache._get_account_info("default")["partition"]
        self.assertEqual(partition, "aws-us-gov")

        mock__get_partition.return_value = ("aws-cn", "cn-north-1")
        partition = cache._get_account_info("default")["partition"]
        self.assertEqual(partition, "aws-cn")

        mock__get_partition.return_value = ("aws", "us-east-1")
        partition = cache._get_account_info("default")["partition"]
        self.assertEqual(partition, "aws")

        self.assertEqual(3, sts.get_caller_identity.call_count)

        sts.get_caller_identity.side_effect = ClientError(
            error_response={"Error": {"Code": "test"}}, operation_name="test"
        )
        with self.assertRaises(ClientError):
            cache._get_account_info("default")

        sts.get_caller_identity.side_effect = ClientError(
            error_response={"Error": {"Code": "AccessDenied"}}, operation_name="test"
        )
        with self.assertRaises(TaskCatException):
            cache._get_account_info("default")

        sts.get_caller_identity.side_effect = NoCredentialsError()
        with self.assertRaises(TaskCatException):
            cache._get_account_info("default")

        sts.get_caller_identity.side_effect = ProfileNotFound(
            profile="non-existent_profile"
        )
        with self.assertRaises(TaskCatException):
            cache._get_account_info("default")

    @mock.patch("taskcat._client_factory.boto3", autospec=True)
    @mock.patch("taskcat._client_factory.Boto3Cache.session")
    def test__get_partition(self, mock_session, mock_boto3):
        session = boto3.Session()
        session.client = mock.Mock()
        sts = mock.Mock()
        sts.get_caller_identity.return_value = {"Account": "123412341234"}
        session.client.return_value = sts
        mock_session.return_value = session
        mock_boto3.session.Session = mock.Mock()
        mock_boto3.session.Session.return_value = session
        cache = Boto3Cache(_boto3=mock_boto3)

        invalid_token_exception = ClientError(
            error_response={"Error": {"Code": "InvalidClientTokenId"}},
            operation_name="test",
        )

        sts.get_caller_identity.side_effect = [True]
        result = cache._get_partition("default")
        self.assertEqual(result, ("aws", "us-east-1"))

        sts.get_caller_identity.side_effect = [invalid_token_exception, True]
        result = cache._get_partition("default")
        self.assertEqual(result, ("aws-cn", "cn-north-1"))

        sts.get_caller_identity.side_effect = [
            invalid_token_exception,
            invalid_token_exception,
            True,
        ]
        result = cache._get_partition("default")
        self.assertEqual(result, ("aws-us-gov", "us-gov-west-1"))
        self.assertEqual(sts.get_caller_identity.call_count, 6)
