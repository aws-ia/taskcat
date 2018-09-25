from __future__ import print_function

import unittest
import mock

from taskcat.client_factory import ClientFactory
from taskcat.cfn_logutils import CfnLogTools
from botocore.exceptions import ClientError
import random


def client_factory_instance():
    with mock.patch.object(ClientFactory, '__init__', return_value=None):
        aws_clients = ClientFactory(None)
    aws_clients._credential_sets = {'default': [None, None, None, None]}
    return aws_clients


def cfn_logutils_instance():
    return CfnLogTools(client_factory_instance())


def mock_boto_get(service, region):
    return MockCfn()


def mock_get_resources(self, stackname, region, include_stacks=False):
    return []


def mock_get_cfn_stack_events(self, stackid, region):
    return [{
            "Timestamp": None,
            "ResourceStatus": None,
            "ResourceType": None,
            "LogicalResourceId": None
        }]


def mock_get_cfnlogs(self, stackid, region):
    return [{
            "TimeStamp": None,
            "ResourceStatus": None,
            "ResourceType": None,
            "LogicalResourceId": None,
            'ResourceStatusReason': ''
        }]


def mock_parse_stack_info(self):
    return {'stack_name': "test_stack", 'region': "us-east-1"}

class MockCfn(object):

    def __init__(self):
        pass

    def describe_stack_events(self, StackName, NextToken=None):
        outp = {"StackEvents": []}
        if StackName == "test_stack" and NextToken:
            outp["StackEvents"].append({})
        elif StackName == "test_stack":
            outp["NextToken"] = "test_token"
        elif StackName == "test_client_error":
            raise ClientError({}, "")
        return outp


class TestCfnLogTools(unittest.TestCase):

    def test___init__(self):
        client_factory = client_factory_instance()

        msg = "should store client factory in self._boto_client"
        cfn_resource = CfnLogTools(client_factory)
        self.assertEqual(client_factory, cfn_resource._boto_client, msg)

    def test_get_cfn_stack_events(self):
        cfn_logutils = cfn_logutils_instance()
        cfn_logutils._boto_client.get = mock_boto_get

        msg = "should return a list of events"
        resources = cfn_logutils.get_cfn_stack_events("test_stack", "us-east-1")
        self.assertEqual([{}], resources, msg)

        msg = "should swallow ClientError and return an ekpty list"
        resources = cfn_logutils.get_cfn_stack_events("test_client_error", "us-east-1")
        self.assertEqual([], resources, msg)

    def test_get_cfnlogs(self):
        cfn_logutils = cfn_logutils_instance()

        msg = "should return the expected output"
        with mock.patch("taskcat.cfn_logutils.CfnLogTools.get_cfn_stack_events", mock_get_cfn_stack_events):
            resources = cfn_logutils.get_cfnlogs("test_stack", "us-east-1")
        expected = [{
            "TimeStamp": None,
            "ResourceStatus": None,
            "ResourceType": None,
            "LogicalResourceId": None,
            'ResourceStatusReason': ''
        }]
        self.assertEqual(expected, resources, msg)

    def test_write_logs(self):
        cfn_logutils = cfn_logutils_instance()

        msg = "should write the expected output to a file"
        path = "/tmp/taskcat_test_write_logs_" + str(random.randrange(1, 1000000000000000))
        with mock.patch("taskcat.cfn_logutils.CfnLogTools.get_cfnlogs", mock_get_cfnlogs):
            with mock.patch("taskcat.common_utils.CommonTools.parse_stack_info", mock_parse_stack_info):
                with mock.patch("taskcat.cfn_resources.CfnResourceTools.get_resources", mock_get_resources):
                    cfn_logutils.write_logs("test_stack", path)
        f = open(path, 'r')
        actual = f.read()
        f.close()
        expected = [
            '-----------------------------------------------------------------------------\n'
            'Region: us-east-1\n'
            'StackName: test_stack\n'
            '*****************************************************************************\n'
            'ResourceStatusReason:  \n'
            '\n'
            '*****************************************************************************\n'
            '*****************************************************************************\n'
            'Events:  \n'
        ]
        self.assertEqual(actual.startswith(expected[0]), True, msg)
