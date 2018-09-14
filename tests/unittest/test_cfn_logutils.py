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
from taskcat.cfn_logutils import CfnResourceTools


def client_factory_instance():
    with mock.patch.object(ClientFactory, '__init__', return_value=None):
        aws_clients = ClientFactory(None)
    aws_clients._credential_sets = {'default': [None, None, None, None]}
    return aws_clients


def cfn_resource_tools_instance():
    return CfnResourceTools(client_factory_instance())


def mock_get_resources_helper(self, stackname, region, l_resources, include_stacks):
    l_resources.append("test_resource")


class TestCfnResourceTools(unittest.TestCase):

    def test___init__(self):
        client_factory = client_factory_instance()

        msg = "should store client factory in self._boto_client"
        cfn_resource = CfnResourceTools(client_factory)
        self.assertEqual(client_factory, cfn_resource._boto_client, msg)

    def test_get_resources(self):
        cfn_resource_tools = cfn_resource_tools_instance()

        msg = "should return a list of resources"
        with mock.patch("taskcat.cfn_logutils.CfnResourceTools.get_resources_helper", mock_get_resources_helper):
            resources = cfn_resource_tools.get_resources("test_stack", "us-east-1")
        self.assertEqual(["test_resource"], resources, msg)
