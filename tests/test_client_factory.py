# -*- coding: UTF-8 -*-

import unittest

import mock
from taskcat._client_factory import Boto3Cache


class TestBoto3Cache(unittest.TestCase):
    @mock.patch("taskcat._client_factory.boto3", autospec=True)
    def test_stable_concurrency(self, mock_boto3):
        # Sometimes boto fails with KeyErrors under high concurrency
        for key_error in ["endpoint_resolver", "credential_provider"]:
            mock_boto3.Session.side_effect = [KeyError(key_error), mock.DEFAULT]
            c = Boto3Cache(_boto3=mock_boto3)
            c.session("default")
