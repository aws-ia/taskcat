import logging
import uuid
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool
from typing import Dict, List

import boto3

from taskcat._cfn.stack import Stack, Stacks, StackStatus
from taskcat._client_factory import Boto3Cache
from taskcat._common_utils import merge_dicts
from taskcat._dataclasses import Tag, TestObj, TestRegion
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


def fan_out(func, partial_kwargs, payload, threads):
    pool = ThreadPool(threads)
    if partial_kwargs:
        func = partial(func, **partial_kwargs)
    results = pool.map(func, payload)
    pool.close()
    pool.join()
    return results


class Stacker:

    NULL_UUID = uuid.UUID(int=0)

    def __init__(
        self,
        project_name: str,
        tests: Dict[str, TestObj],
        uid: uuid.UUID = NULL_UUID,
        stack_name_prefix: str = "tCaT",
        shorten_stack_name: bool = False,
        tags: list = None,
    ):
        self.tests = tests
        self.project_name = project_name
        self.stack_name_prefix = stack_name_prefix
        self.shorten_stack_name = shorten_stack_name
        self.tags = tags if tags else []
        self.uid = uuid.uuid4() if uid == Stacker.NULL_UUID else uid
        self.stacks: Stacks = Stacks()

    @staticmethod
    def _tests_to_list(tests: Dict[str, TestObj]):
        return list(tests.values())

    def create_stacks(self, threads: int = 8):
        if self.stacks:
            raise TaskCatException("Stacker already initialised with stack objects")
        tests = self._tests_to_list(self.tests)
        tags = [Tag({"Key": "taskcat-id", "Value": self.uid.hex})]
        tags += [
            Tag(t)
            for t in self.tags
            if t.key not in ["taskcat-project-name", "taskcat-test-name", "taskcat-id"]
        ]
        fan_out(self._create_stacks_for_test, {"tags": tags}, tests, threads)

    def _create_stacks_for_test(self, test, tags, threads: int = 32):
        stack_name = test.stack_name
        tags.append(Tag({"Key": "taskcat-project-name", "Value": self.project_name}))
        tags.append(Tag({"Key": "taskcat-test-name", "Value": test.name}))
        tags += test.tags
        partial_kwargs = {
            "stack_name": stack_name,
            "template": test.template,
            "tags": tags,
            "test_name": test.name,
        }
        stacks = fan_out(Stack.create, partial_kwargs, test.regions, threads)
        self.stacks += stacks

    # Not used by tCat at present
    def update_stacks(self):
        raise NotImplementedError()

    def delete_stacks(self, criteria: dict = None, deep=False, threads=32):
        if deep:
            raise NotImplementedError("deep delete not yet implemented")
        fan_out(
            self._delete_stacks_per_client,
            None,
            self._group_stacks(self.stacks.filter(criteria)),
            threads,
        )

    def _delete_stacks_per_client(self, stacks, threads=8):
        fan_out(self._delete_stack, None, stacks["Stacks"], threads)

    @staticmethod
    def _delete_stack(stack: Stack):
        stack.delete(stack_id=stack.id, client=stack.client)
        stack.refresh()

    def status(self, recurse: bool = False, threads: int = 32, **kwargs):
        if recurse:
            raise NotImplementedError("recurse not implemented")
        stacks = self.stacks.filter(kwargs)
        per_region_stacks = self._group_stacks(stacks)
        results = fan_out(self._status_per_client, None, per_region_stacks, threads)
        statuses: Dict[str, dict] = {"IN_PROGRESS": {}, "COMPLETE": {}, "FAILED": {}}
        for region in results:
            for status in region:
                statuses[status[1]][status[0]] = status[2]
        return statuses

    def _status_per_client(self, stacks, threads: int = 8):
        return fan_out(self._status, None, stacks["Stacks"], threads)

    @staticmethod
    def _status(stack: Stack):
        for status_group in ["COMPLETE", "IN_PROGRESS", "FAILED"]:
            if stack.status in getattr(StackStatus, status_group):
                return stack.id, status_group, stack.status_reason
        raise TaskCatException(f"Invalid stack {stack}")

    def events(self, recurse=False, threads: int = 32, **kwargs):
        if recurse:
            raise NotImplementedError("recurse not implemented")
        per_region_stacks = self._group_stacks(self.stacks)
        results = fan_out(
            self._events_per_client, {"criteria": kwargs}, per_region_stacks, threads
        )
        return merge_dicts(results)

    def _events_per_client(self, stacks, criteria, threads: int = 8):
        results = fan_out(
            self._describe_stack_events,
            {"criteria": criteria},
            stacks["Stacks"],
            threads,
        )
        return merge_dicts(results)

    @staticmethod
    def _describe_stack_events(stack: Stack, criteria):
        return {stack.id: stack.events().filter(criteria)}

    def resources(self, recurse=False, threads: int = 32, **kwargs):
        if recurse:
            raise NotImplementedError("recurse not implemented")
        results = fan_out(
            self._resources_per_client,
            {"criteria": kwargs},
            self._group_stacks(self.stacks),
            threads,
        )
        return merge_dicts(results)

    def _resources_per_client(self, stacks, criteria, threads: int = 8):
        results = fan_out(
            self._resources, {"criteria": criteria}, stacks["Stacks"], threads
        )
        return merge_dicts(results)

    @staticmethod
    def _resources(stack: Stack, criteria):
        return {stack.id: stack.resources().filter(criteria)}

    @classmethod
    def from_existing(
        cls,
        uid: uuid.UUID,
        project_name: str,
        tests: Dict[str, TestObj],
        include_deleted=False,
        recurse=False,
        threads=32,
    ):
        if include_deleted:
            raise NotImplementedError("including deleted stacks not implemented")
        if recurse:
            raise NotImplementedError("recurse not implemented")
        clients: Dict[boto3.client, List[TestRegion]] = {}
        for test in tests.values():
            for region in test.regions:
                client = region.client("cloudformation")
                if client not in clients:
                    clients[client] = []
                clients[client].append(region)
        results = fan_out(
            Stacker._import_stacks_per_client,
            {"uid": uid, "project_name": project_name, "tests": tests},
            clients.items(),
            threads,
        )
        stacker = Stacker(project_name, tests, uid)
        stacker.stacks = Stacks([item for sublist in results for item in sublist])
        return stacker

    @staticmethod
    def _import_stacks_per_client(clients, uid, project_name, tests):
        # pylint: disable=too-many-locals
        stacks = Stacks()
        client, region = clients
        for page in client.get_paginator("describe_stacks").paginate():
            for stack_props in page["Stacks"]:
                if stack_props.get("ParentId"):
                    continue
                match = False
                project = ""
                test = ""
                for tag in stack_props["Tags"]:
                    k, v = (tag["Key"], tag["Value"])
                    if k == "taskcat-id" and v == uid.hex:
                        match = True
                    elif k == "taskcat-test-name" and v in tests:
                        test = v
                    elif k == "taskcat-project-name" and v == project_name:
                        project = v
                if match and test and project:
                    stack = Stack.import_existing(
                        stack_props, tests[test].template, region[0], test, uid,
                    )
                    stacks.append(stack)
        return stacks

    @staticmethod
    def _group_stacks(stacks: Stacks) -> List[dict]:
        stacks_by_client: dict = {}
        for stack in stacks:
            client = stack.client
            if client not in stacks_by_client:
                stacks_by_client[client] = {"Client": client, "Stacks": []}
            stacks_by_client[client]["Stacks"].append(stack)
        return [stacks_by_client[r] for r in stacks_by_client]

    @staticmethod
    def list_stacks(profiles, regions):
        stacks = fan_out(
            Stacker._list_per_profile,
            {"regions": regions, "boto_cache": Boto3Cache()},
            profiles,
            threads=8,
        )
        return [stack for sublist in stacks for stack in sublist]

    @staticmethod
    def _list_per_profile(profile, regions, boto_cache):
        stacks = fan_out(
            Stacker._get_taskcat_stacks,
            {"boto_cache": boto_cache, "profile": profile},
            regions,
            threads=len(regions),
        )
        return [stack for sublist in stacks for stack in sublist]

    @staticmethod
    def _get_taskcat_stacks(region, boto_cache: Boto3Cache, profile: str):
        stacks = []
        try:
            cfn = boto_cache.client("cloudformation", profile=profile, region=region)
            for page in cfn.get_paginator("describe_stacks").paginate():
                for stack_props in page["Stacks"]:
                    if stack_props.get("ParentId"):
                        continue
                    stack_id = stack_props["StackId"]
                    stack_name = stack_id.split("/")[1]
                    stack = {
                        "region": region,
                        "profile": profile,
                        "stack-id": stack_id,
                        "stack-name": stack_name,
                    }
                    for tag in stack_props["Tags"]:
                        k, v = (tag["Key"], tag["Value"])
                        if k.startswith("taskcat-"):
                            stack[k] = v
                    if stack.get("taskcat-id"):
                        stack["taskcat-id"] = uuid.UUID(stack["taskcat-id"])
                        stacks.append(stack)
        except Exception as e:  # pylint: disable=broad-except
            LOG.warning(
                f"Failed to fetch stacks for region {region} using profile "
                f"{profile} {type(e)} {e}"
            )
            LOG.debug("Traceback:", exc_info=True)
        return stacks
