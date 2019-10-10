import unittest
import uuid
from pathlib import Path

import mock
from taskcat import Config
from taskcat._cfn.threaded import Stacker


def return_mock(*args, **kwargs):
    return mock.Mock()


@mock.patch(
    "taskcat._dataclasses.S3BucketObj._bucket_matches_existing", return_value=True
)
def get_tests(test_proj, _):
    c = Config.create(
        project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
    )
    boto_cache = get_mock_boto_cache()
    templates = c.get_templates(project_root=test_proj)
    regions = c.get_regions(boto3_cache=boto_cache)
    buckets = c.get_buckets(boto_cache)
    params = c.get_rendered_parameters(buckets, regions, templates)
    return (
        c.config.project.name,
        c.get_tests(
            project_root=test_proj,
            templates=templates,
            regions=regions,
            buckets=buckets,
            parameters=params,
        ),
    )


@mock.patch("taskcat._client_factory.Boto3Cache", autospec=True)
def get_mock_boto_cache(m_boto):
    return m_boto()


class TestStacker(unittest.TestCase):
    @mock.patch("taskcat._cfn.threaded.Stack.create", return_mock)
    def test_create_stacks(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        project_name, tests = get_tests(test_proj)
        stacker = Stacker(project_name=project_name, tests=tests)
        stacker.create_stacks()
        self.assertEqual(2, len(stacker.stacks))

    @mock.patch("taskcat._cfn.threaded.Stack.create", return_mock)
    def test_delete_stacks(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        project_name, tests = get_tests(test_proj)
        stacker = Stacker(project_name=project_name, tests=tests)
        stacker.create_stacks()
        stacker.delete_stacks()
        stacker.stacks[0].delete.assert_called_once()

    @mock.patch("taskcat._cfn.threaded.Stack.create", return_mock)
    def test_status(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        project_name, tests = get_tests(test_proj)
        stacker = Stacker(project_name=project_name, tests=tests)
        stacker.create_stacks()
        stacker.stacks[0].id = "stack-id"
        stacker.stacks[0].status_reason = ""
        stacker.stacks[0].status = "CREATE_COMPLETE"
        stacker.stacks[1].id = "stack-id2"
        stacker.stacks[1].status_reason = ""
        stacker.stacks[1].status = "CREATE_IN_PROGRESS"
        statuses = stacker.status()
        expected = {
            "COMPLETE": {"stack-id": ""},
            "FAILED": {},
            "IN_PROGRESS": {"stack-id2": ""},
        }
        self.assertEqual(expected, statuses)

    @mock.patch("taskcat._cfn.threaded.Stack.create", return_mock)
    def test_events(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        project_name, tests = get_tests(test_proj)
        stacker = Stacker(project_name=project_name, tests=tests)
        stacker.create_stacks()
        events = stacker.events()
        self.assertEqual(2, len(events))

    @mock.patch("taskcat._cfn.threaded.Stack.create", return_mock)
    def test_resources(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        project_name, tests = get_tests(test_proj)
        stacker = Stacker(project_name=project_name, tests=tests)
        stacker.create_stacks()
        resources = stacker.resources()
        self.assertEqual(2, len(resources))

    @mock.patch("taskcat._dataclasses.RegionObj.client", return_mock)
    @mock.patch(
        "taskcat._cfn.threaded.Stacker._import_stacks_per_client", return_value=[]
    )
    def test_from_existing(self, m_import):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        project_name, tests = get_tests(test_proj)
        s = Stacker.from_existing(
            uid=uuid.UUID(int=0), tests=tests, project_name=project_name
        )
        self.assertEqual([], s.stacks)

    @mock.patch("taskcat._cfn.threaded.Stack.import_existing")
    def test_import_stacks_per_client(self, m_stack_import):
        clients = (mock.Mock(), "us-east-1")

        class Paging:
            @staticmethod
            def paginate(**kwargs):
                return [
                    {
                        "Stacks": [
                            {"ParentId": "skipme"},
                            {
                                "Tags": [
                                    {
                                        "Key": "taskcat-id",
                                        "Value": "00000000000000000000000000000000",
                                    },
                                    {
                                        "Key": "taskcat-test-name",
                                        "Value": "taskcat-json",
                                    },
                                    {
                                        "Key": "taskcat-project-name",
                                        "Value": "nested-fail",
                                    },
                                ]
                            },
                            {
                                "Tags": [
                                    {"Key": "taskcat-id", "Value": "nope"},
                                    {
                                        "Key": "taskcat-test-name",
                                        "Value": "taskcat-json",
                                    },
                                    {
                                        "Key": "taskcat-project-name",
                                        "Value": "nested-fail",
                                    },
                                ]
                            },
                            {
                                "Tags": [
                                    {
                                        "Key": "taskcat-id",
                                        "Value": "00000000000000000000000000000000",
                                    },
                                    {"Key": "taskcat-test-name", "Value": "nope"},
                                    {
                                        "Key": "taskcat-project-name",
                                        "Value": "nested-fail",
                                    },
                                ]
                            },
                            {
                                "Tags": [
                                    {
                                        "Key": "taskcat-id",
                                        "Value": "00000000000000000000000000000000",
                                    },
                                    {
                                        "Key": "taskcat-test-name",
                                        "Value": "taskcat-json",
                                    },
                                    {"Key": "taskcat-project-name", "Value": "nope"},
                                ]
                            },
                        ]
                    }
                ]

        clients[0].get_paginator.return_value = Paging()
        s = Stacker._import_stacks_per_client(
            clients, uuid.UUID(int=0), "nested-fail", {"taskcat-json": mock.Mock()}
        )
        self.assertEqual(1, len(s))
