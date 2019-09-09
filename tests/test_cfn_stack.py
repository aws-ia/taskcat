import unittest
from datetime import datetime
from pathlib import Path
from threading import Timer

import mock

from taskcat import Config
from taskcat._cfn.stack import (
    AWSRegionObject,
    Event,
    Events,
    Output,
    Parameter,
    Resource,
    Resources,
    Stack,
    Tag,
    Tags,
    criteria_matches,
)

event_template = {
    "EventId": "test_event_id",
    "StackName": "test_stack_name",
    "LogicalResourceId": "test_logical_id",
    "ResourceType": "test_resource_type",
    "ResourceStatus": "CREATE_IN_PROGRESS",
}

resource_template = {
    "LogicalResourceId": "test_logical_id",
    "ResourceType": "test_resource_type",
    "ResourceStatus": "CREATE_IN_PROGRESS",
}


class TestCriteriaMatcher(unittest.TestCase):
    def test_criteria_matches(self):
        with self.assertRaises(ValueError) as cm:
            tag = Tag({"Key": "my_key", "Value": "my_value"})
            criteria_matches({"invalid": "blah"}, tag)
        self.assertEqual(
            "invalid is not a valid property of <class 'taskcat._cfn.stack.Tag'>",
            str(cm.exception),
        )

        actual = criteria_matches({"key": "blah"}, tag)
        self.assertEqual(actual, False)
        actual = criteria_matches({"key": "my_key"}, tag)
        self.assertEqual(actual, True)
        actual = criteria_matches({"key": "my_key", "value": "blah"}, tag)
        self.assertEqual(actual, False)
        actual = criteria_matches({"key": "my_key", "value": "my_value"}, tag)
        self.assertEqual(actual, True)


class TestEvent(unittest.TestCase):
    def test_event(self):
        event_dict = event_template.copy()
        event = Event(event_dict)
        self.assertEqual(event.physical_id, "")
        self.assertEqual(event.properties, {})
        self.assertEqual(event.status_reason, "")
        self.assertEqual(event.timestamp, datetime.fromtimestamp(0))
        event_dict["PhysicalResourceId"] = "test_id"
        now = datetime.now()
        event_dict["Timestamp"] = now
        event_dict["ResourceStatusReason"] = "test_reason"
        event_dict["ResourceProperties"] = '{"test_prop_key": "test_value"}'
        event = Event(event_dict)
        self.assertEqual(event.physical_id, "test_id")
        self.assertEqual(event.properties, {"test_prop_key": "test_value"})
        self.assertEqual(event.status_reason, "test_reason")
        self.assertEqual(event.timestamp, now)

        expected = "{} {} {}".format(now, "test_logical_id", "CREATE_IN_PROGRESS")
        self.assertEqual(expected, str(event))
        expected = "<Event object {} at {}>".format("test_event_id", hex(id(event)))
        self.assertEqual(expected, event.__repr__())


class TestResource(unittest.TestCase):
    def test_resource(self):
        resource_dict = resource_template.copy()
        resource = Resource("test_stack_id", resource_dict)
        self.assertEqual(resource.logical_id, "test_logical_id")
        self.assertEqual(resource.physical_id, "")
        self.assertEqual(resource.status_reason, "")
        self.assertEqual(resource.last_updated_timestamp, datetime.fromtimestamp(0))
        resource_dict["PhysicalResourceId"] = "test_pid"
        now = datetime.now()
        resource_dict["LastUpdatedTimestamp"] = now
        resource_dict["ResourceStatusReason"] = "test_reason"
        resource = Resource("test_stack_id", resource_dict)
        self.assertEqual(resource.physical_id, "test_pid")
        self.assertEqual(resource.status_reason, "test_reason")
        self.assertEqual(resource.last_updated_timestamp, now)


class TestParameter(unittest.TestCase):
    def test_parameter(self):
        param_dict = {"ParameterKey": "test_key"}
        param = Parameter(param_dict)
        self.assertEqual(param.key, "test_key")
        self.assertEqual(param.value, "")
        self.assertEqual(param.raw_value, "")
        self.assertEqual(param.use_previous_value, False)
        self.assertEqual(param.resolved_value, "")
        param_dict["ParameterValue"] = "test_value"
        param_dict["UsePreviousValue"] = True
        param_dict["ResolvedValue"] = "test_resolved_value"
        param = Parameter(param_dict)
        self.assertEqual(param.value, "test_value")
        self.assertEqual(param.raw_value, "test_value")
        self.assertEqual(param.use_previous_value, True)
        self.assertEqual(param.resolved_value, "test_resolved_value")

    def test_dump(self):
        param_dict = {
            "ParameterKey": "test_key",
            "ParameterValue": "test_val",
            "UsePreviousValue": True,
        }
        param = Parameter(param_dict)
        actual = param.dump()
        self.assertEqual(param_dict, actual)


class TestOutput(unittest.TestCase):
    def test_output(self):
        output_dict = {"OutputKey": "test_key", "OutputValue": "test_value"}
        output = Output(output_dict)
        self.assertEqual(output.key, "test_key")
        self.assertEqual(output.value, "test_value")
        self.assertEqual(output.description, "")
        self.assertEqual(output.export_name, "")
        output_dict["Description"] = "test_desc"
        output_dict["ExportName"] = "test_export"
        output = Output(output_dict)
        self.assertEqual(output.description, "test_desc")
        self.assertEqual(output.export_name, "test_export")


class TestTag(unittest.TestCase):
    def test_tag(self):
        tag_dict = {"Key": "my_key", "Value": "my_value"}
        tag = Tag(tag_dict)
        self.assertEqual(tag.key, "my_key")
        self.assertEqual(tag.value, "my_value")
        actual = tag.dump()
        self.assertEqual(tag_dict, actual)


class TestFilterableList(unittest.TestCase):
    def test_filterable_list(self):
        tags = Tags([Tag({"Key": "my_key", "Value": "my_value"})])
        filtered = tags.filter()
        self.assertEqual(filtered, tags)
        filtered = tags.filter({"key": "blah"})
        self.assertEqual(filtered, [])
        filtered = tags.filter({"key": "my_key"})
        self.assertEqual(filtered, tags)
        filtered = tags.filter(key="my_key", value="blah")
        self.assertEqual(filtered, [])
        filtered = tags.filter(key="my_key", value="my_value")
        self.assertEqual(filtered, tags)


def mock_client_method(*args, **kwargs):
    m_client = mock.Mock()
    if args[0] == "cloudformation":
        m_client.create_stack.return_value = {
            "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/"
            "SampleStack/e722ae60-fe62-11e8-9a0e-0ae8cc519968"
        }
        m_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Tags": [{"Key": "tag_key", "Value": "tag_value"}],
                    "Parameters": [
                        {"ParameterKey": "MyParam", "ParameterValue": "MyVal"}
                    ],
                    "Outputs": [
                        {"OutputKey": "MyOutput", "OutputValue": "MyOutputValue"}
                    ],
                    "StackStatus": "CREATE_IN_PROGRESS",
                }
            ]
        }

        class Paging:
            def __init__(self, api):
                self._api = api

            def paginate(self, **kwargs):
                if self._api == "describe_stacks":
                    return [
                        {
                            "Stacks": [
                                {
                                    "StackId": "arn:aws:cloudformation:us-east-1:"
                                    "123456789012:stack/Child/e722ae60-fe62-11e8-"
                                    "9a0e-0ae8cc519969",
                                    "ParentId": "arn:aws:cloudformation:us-east-1:"
                                    "123456789012:stack/SampleStack/e722ae60-fe62-"
                                    "11e8-9a0e-0ae8cc519968",
                                },
                                {
                                    "StackId": "arn:aws:cloudformation:us-east-1:"
                                    "123456789012:stack/GrandChild/e722ae60-fe62-11e8-"
                                    "9a0e-0ae8cc519970",
                                    "ParentId": "arn:aws:cloudformation:us-east-1:"
                                    "123456789012:stack/Child/e722ae60-fe62-11e8-"
                                    "9a0e-0ae8cc519969",
                                },
                            ]
                        }
                    ]
                raise NotImplementedError(self._api)

        m_client.get_paginator = Paging
    return m_client


class TestStack(unittest.TestCase):
    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    def test_create(self, m_s3_url_maker):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.create(region, "stack_name", m_template)
        self.assertIsInstance(stack._timer, Timer)
        self.assertEqual(stack._timer.is_alive(), True)
        stack._timer.cancel()
        m_s3_url_maker.assert_called_once()

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    def test_idempotent_properties(self, _):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.create(region, "stack_name", m_template)
        stack._timer.cancel()
        # re-invoke timer function manually to check for idempotence
        stack.set_stack_properties()
        stack._timer.cancel()
        self.assertEqual(len(stack.outputs), 1)
        self.assertEqual(len(stack.parameters), 1)
        self.assertEqual(len(stack.tags), 1)

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    def test_import_existing(self, _):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.import_existing(
            {
                "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/"
                "SampleStack/e722ae60-fe62-11e8-9a0e-0ae8cc519968"
            },
            m_template,
            region,
            "test_test",
            mock.Mock(),
        )
        stack._timer.cancel()
        self.assertEqual(stack.name, "SampleStack")

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    @mock.patch("taskcat._cfn.stack.Stack.set_stack_properties")
    @mock.patch("taskcat._cfn.stack.Stack._fetch_stack_events")
    @mock.patch("taskcat._cfn.stack.Stack._fetch_stack_resources")
    @mock.patch("taskcat._cfn.stack.Stack._fetch_children")
    def test_refresh(self, m_kids, m_res, m_eve, m_prop, _):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.create(region, "stack_name", m_template)
        stack._timer.cancel()

        m_prop.reset_mock()
        stack.refresh()
        m_prop.assert_called_once()
        m_res.assert_not_called()
        m_eve.assert_not_called()
        m_kids.assert_not_called()

        m_prop.reset_mock()
        stack.refresh(properties=False, events=True)
        m_eve.assert_called_once()
        m_res.assert_not_called()
        m_prop.assert_not_called()
        m_kids.assert_not_called()

        m_eve.reset_mock()
        stack.refresh(properties=False, resources=True)
        m_res.assert_called_once()
        m_eve.assert_not_called()
        m_prop.assert_not_called()
        m_kids.assert_not_called()

        m_res.reset_mock()
        stack.refresh(properties=False, children=True)
        m_kids.assert_called_once()
        m_res.assert_not_called()
        m_prop.assert_not_called()
        m_res.assert_not_called()

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    @mock.patch("taskcat._cfn.stack.Stack._fetch_stack_events")
    def test_events(self, m_eve, _):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.create(region, "stack_name", m_template)
        stack._timer.cancel()
        generic_evnt = event_template.copy()
        not_generic_evnt = event_template.copy()
        generic_evnt["ResourceStatusReason"] = "Resource creation cancelled"
        generic_evnt["LogicalResourceId"] = "generic"
        not_generic_evnt["LogicalResourceId"] = "not-generic"
        stack._events = Events([Event(generic_evnt), Event(not_generic_evnt)])

        actual = stack.events()
        m_eve.assert_called_once()
        self.assertEqual(len(actual), 2)

        stack._last_event_refresh = datetime.now()
        actual = stack.events(include_generic=False)
        m_eve.assert_called_once()
        self.assertEqual(len(actual), 1)

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    @mock.patch("taskcat._cfn.stack.Event")
    def test_fetch_stack_events(self, n_evnt, _):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.create(region, "stack_name", m_template)
        stack._timer.cancel()
        stack.client = mock.Mock()

        class Paging:
            @staticmethod
            def paginate(**kwargs):
                return [
                    {
                        "StackEvents": [
                            {
                                "StackId": "arn:aws:cloudformation:us-east-1:"
                                "123456789012:stack/"
                                "SampleStack/e722ae60-fe62-11e8-9a0e-0ae8cc519968"
                            }
                        ]
                    }
                ]

        stack.client.get_paginator.return_value = Paging()
        stack._fetch_stack_events()
        stack.client.get_paginator.assert_called_once()
        self.assertEqual(len(stack._events), 1)

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    @mock.patch("taskcat._cfn.stack.Stack._fetch_stack_resources")
    def test_resources(self, m_res, _):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.create(region, "stack_name", m_template)
        stack._timer.cancel()
        stack._resources = Resources([Resource("test_stack_id", resource_template)])

        stack.resources()
        m_res.assert_called_once()

        stack._last_resource_refresh = datetime.now()
        stack.resources()
        m_res.assert_called_once()

        m_res.reset_mock()
        stack.resources(refresh=True)
        m_res.assert_called_once()

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    @mock.patch("taskcat._cfn.stack.Resource")
    def test_fetch_stack_resources(self, _, __):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.create(region, "stack_name", m_template)
        stack._timer.cancel()
        stack.client = mock.Mock()

        class Paging:
            @staticmethod
            def paginate(**kwargs):
                return [
                    {
                        "StackResourceSummaries": [
                            {
                                "StackId": "arn:aws:cloudformation:us-east-1:"
                                "123456789012:stack/"
                                "SampleStack/e722ae60-fe62-11e8-9a0e-0ae8cc519968"
                            }
                        ]
                    }
                ]

        stack.client.get_paginator.return_value = Paging()
        stack._fetch_stack_resources()
        stack.client.get_paginator.assert_called_once()
        self.assertEqual(len(stack._resources), 1)

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    @mock.patch("taskcat._cfn.stack.Stack.refresh")
    def test_delete(self, _, __):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        m_template = mock.Mock()
        stack = Stack.create(region, "stack_name", m_template)
        stack._timer.cancel()
        stack.client = mock.Mock()

        stack.refresh.reset_mock()
        stack.delete()
        stack.client.delete_stack.assert_called_once()
        stack.refresh.assert_called_once()

    @mock.patch(
        "taskcat._cfn.stack.s3_url_maker",
        return_value="https://test.s3.amazonaws.com/prefix/object",
    )
    @mock.patch("taskcat._cfn.stack.Stack.events")
    def test_descentants(self, m_evnts, __):
        m_cf = mock.Mock()
        region = AWSRegionObject("us-west-2", m_cf)
        region.s3bucket = mock.Mock()
        region.client = mock_client_method
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config(
            project_config_path=test_proj / "ci" / "taskcat.yml",
            project_root=test_proj,
            create_clients=False,
        )
        stack = Stack.create(region, "stack_name", c.tests["taskcat-json"].template)
        stack._timer.cancel()

        child = event_template.copy()
        grandchild = event_template.copy()
        child["PhysicalResourceId"] = (
            "arn:aws:cloudformation:us-east-1:123456789012:"
            "stack/Child/e722ae60-fe62-11e8-9a0e-0ae8cc519969"
        )
        child["ResourceProperties"] = (
            '{"TemplateURL": "https://test.s3.amazonaws.com/templates/'
            'test.template_inner.yaml"}'
        )
        grandchild["PhysicalResourceId"] = (
            "arn:aws:cloudformation:us-east-1:123456789012:stack/GrandChild/"
            "e722ae60-fe62-11e8-9a0e-0ae8cc519970"
        )
        grandchild["ResourceProperties"] = (
            '{"TemplateURL": "https://test.s3.amazonaws.com/templates/'
            'test.template_middle.yaml"}'
        )
        m_evnts.return_value = Events([Event(child), Event(grandchild)])

        desc = stack.descendants()
        self.assertEqual(len(desc), 2)
