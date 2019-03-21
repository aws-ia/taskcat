#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function

import unittest
import mock
from taskcat.client_factory import ClientFactory
from taskcat.cfn_resources import CfnResourceTools
from taskcat.exceptions import TaskCatException


def client_factory_instance():
    with mock.patch.object(ClientFactory, '__init__', return_value=None):
        aws_clients = ClientFactory(None)
    aws_clients._credential_sets = {'default': [None, None, None, None]}
    return aws_clients


def cfn_resource_tools_instance():
    return CfnResourceTools(client_factory_instance())


def mock_get_resources_helper(self, stackname, region, l_resources, include_stacks):
    l_resources.append("test_resource")


def mock_get_resources(self, stackname, region, include_stacks=False):
    return []


def mock_boto_get(service, region):
    return MockCfn()


class MockCfn(object):

    def __init__(self):
        pass

    def describe_stack_resources(self, StackName):
        outp = {"StackResources": []}
        if StackName == "test_stack":
            outp["StackResources"].append({
                        "ResourceType": "test_type",
                        "PhysicalResourceId": "test_pid",
                        "LogicalResourceId": "test_lid"
                    })
        elif StackName == "test_nested_stack":
            outp["StackResources"].append({
                "ResourceType": "AWS::CloudFormation::Stack",
                "PhysicalResourceId": "test_stack",
                "LogicalResourceId": "test_stack"
            })
        elif StackName == "test_raise":
            raise ValueError
        elif StackName == "test_raise_tcat":
            raise TaskCatException
        return outp


class TestCfnResourceTools(unittest.TestCase):

    def test___init__(self):
        client_factory = client_factory_instance()

        msg = "should store client factory in self._boto_client"
        cfn_resource = CfnResourceTools(client_factory)
        self.assertEqual(client_factory, cfn_resource._boto_client, msg)

    def test_get_resources(self):
        cfn_resource_tools = cfn_resource_tools_instance()

        msg = "should return a list of resources"
        with mock.patch("taskcat.cfn_resources.CfnResourceTools.get_resources_helper", mock_get_resources_helper):
            resources = cfn_resource_tools.get_resources("test_stack", "us-east-1")
        self.assertEqual(["test_resource"], resources, msg)

    def test_get_resources_helper(self):
        cfn_resource_tools = cfn_resource_tools_instance()
        cfn_resource_tools._boto_client.get = mock_boto_get

        msg = "should return expected list of resources"
        actual = []
        cfn_resource_tools.get_resources_helper("test_stack", "us-east-1", actual, False)
        self.assertEqual([{'resourceType': 'test_type', 'physicalId': 'test_pid', 'logicalId': 'test_lid'}], actual, msg)

        msg = "should return expected list of resources"
        actual = []
        cfn_resource_tools.get_resources_helper("test_nested_stack", "us-east-1", actual, True)
        expected = [
            {'logicalId': 'test_stack', 'physicalId': 'test_stack', 'resourceType': 'AWS::CloudFormation::Stack'},
            {'logicalId': 'test_lid', 'physicalId': 'test_pid', 'resourceType': 'test_type'}
        ]
        self.assertEqual(expected, actual, msg)

        msg = "should raise Taskcat error with specific message"
        actual = []
        with self.assertRaises(TaskCatException) as e:
            cfn_resource_tools.get_resources_helper("test_raise", "us-east-1", actual, False)
        self.assertEqual("Unable to get resources for stack test_raise", str(e.exception), msg)

    def test_get_all_resources(self):
        cfn_resource_tools = cfn_resource_tools_instance()

        msg = "should return a list of resources"
        with mock.patch("taskcat.cfn_resources.CfnResourceTools.get_resources", mock_get_resources):
            resources = cfn_resource_tools.get_all_resources(["test_stack"], "us-east-1")
        self.assertEqual([{'resources': [], 'stackId': 'test_stack'}], resources, msg)
