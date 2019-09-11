import logging
import uuid
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool
from typing import Dict, List

import boto3

from taskcat._cfn.stack import Parameter, Stack, Stacks, StackStatus, Tag
from taskcat._common_utils import merge_dicts
from taskcat._config import Config
from taskcat._config_types import AWSRegionObject, Test
from taskcat.exceptions import TaskCatException
from taskcat._client_factory import ClientFactory

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
        config: Config,
        uid: uuid.UUID = NULL_UUID,
        stack_name_prefix: str = "tCaT",
        tags: list = None,
    ):
        self.config = config
        self.project_name = config.name
        self.stack_name_prefix = stack_name_prefix
        self.tags = tags if tags else []
        self.uid = uuid.uuid4() if uid == Stacker.NULL_UUID else uid
        self.stacks: Stacks = Stacks()

    @staticmethod
    def _tests_to_list(tests: Dict[str, Test]):
        return [test for test in tests.values()]

    def create_stacks(self, threads: int = 8):
        if self.stacks:
            raise TaskCatException("Stacker already initialised with stack objects")
        tests = self._tests_to_list(self.config.tests)
        tags = [Tag({"Key": "taskcat-id", "Value": self.uid.hex})]
        tags += [
            Tag(t)
            for t in self.tags
            if t.key not in ["taskcat-project-name", "taskcat-test-name", "taskcat-id"]
        ]
        fan_out(self._create_stacks_for_test, {"tags": tags}, tests, threads)

    def _create_stacks_for_test(self, test, tags, threads: int = 32):
        prefix = f"{self.stack_name_prefix}-" if self.stack_name_prefix else ""
        stack_name = "{}{}-{}-{}".format(
            prefix, self.project_name, test.name, self.uid.hex
        )
        tags.append(Tag({"Key": "taskcat-project-name", "Value": self.project_name}))
        tags.append(Tag({"Key": "taskcat-test-name", "Value": test.name}))
        partial_kwargs = {
            "stack_name": stack_name,
            "template": test.template,
            "parameters": self._cfn_format_parameters(test.parameters),
            "tags": tags,
            "test_name": test.name,
        }
        stacks = fan_out(Stack.create, partial_kwargs, test.regions, threads)
        self.stacks += stacks

    @staticmethod
    def _cfn_format_parameters(parameters):
        return [
            Parameter({"ParameterKey": k, "ParameterValue": v})
            for k, v in parameters.items()
        ]

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
        stack.delete()

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
        config: Config,
        include_deleted=False,
        recurse=False,
        threads=32,
    ):
        if include_deleted:
            raise NotImplementedError("including deleted stacks not implemented")
        if recurse:
            raise NotImplementedError("recurse not implemented")
        clients: Dict[boto3.client, List[AWSRegionObject]] = {}
        for test in config.tests.values():
            for region in test.regions:
                client = region.client("cloudformation")
                if client not in clients:
                    clients[client] = []
                clients[client].append(region)
        results = fan_out(
            Stacker._import_stacks_per_client,
            {"uid": uid, "project_name": config.name, "tests": config.tests},
            clients.items(),
            threads,
        )
        stacker = Stacker(config, uid)
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
                        stack_props, tests[test].template, region[0], test, uid
                    )
                    stacks.append(stack)
        return stacks

    @staticmethod
    def _group_stacks(stacks: Stacks) -> List[dict]:
        stacks_by_client: dict = {}
        for stack in stacks:
            client = stack.region.client
            if client not in stacks_by_client:
                stacks_by_client[client] = {"Client": client, "Stacks": []}
            stacks_by_client[client]["Stacks"].append(stack)
        return [stacks_by_client[r] for r in stacks_by_client]

    @staticmethod
    def list_stacks(profiles, regions):
        stacks = fan_out(
            Stacker._list_per_profile, {"regions": regions}, profiles, threads=8
        )
        return [stack for sublist in stacks for stack in sublist]

    @staticmethod
    def _list_per_profile(profile, regions):
        stacks = fan_out(
            Stacker._get_taskcat_stacks,
            {"boto_factory": ClientFactory(profile_name=profile)},
            regions,
            threads=len(regions),
        )
        return [stack for sublist in stacks for stack in sublist]

    @staticmethod
    def _get_taskcat_stacks(region, boto_factory: ClientFactory):
        cfn = boto_factory.get("cloudformation", region=region)
        stacks = []
        profile = list(boto_factory._credential_sets.keys())[0]
        try:
            for page in cfn.get_paginator("describe_stacks").paginate():
                for stack_props in page["Stacks"]:
                    if stack_props.get("ParentId"):
                        continue
                    stack = {"region": region, "profile": profile}
                    for tag in stack_props["Tags"]:
                        k, v = (tag["Key"], tag["Value"])
                        if k.startswith("taskcat-"):
                            stack[k] = v
                    if stack.get("taskcat-id"):
                        stack["taskcat-id"] = uuid.UUID(stack["taskcat-id"])
                        stacks.append(stack)
        except Exception:
            LOG.warning(
                f"Failed to fetch stacks for region {region} using profile "
                f"{profile}"
            )
            LOG.debug(f"Traceback:", exc_info=True)
        return stacks
