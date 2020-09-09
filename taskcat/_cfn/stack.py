import json
import logging
import os
import random
import re
import string
from datetime import datetime, timedelta
from pathlib import Path
from threading import Timer
from typing import Callable, List, Optional, Tuple
from uuid import UUID, uuid4

import boto3
import yaml

from taskcat._cfn.template import Template, tcat_template_cache
from taskcat._common_utils import ordered_dump, pascal_to_snake, s3_url_maker
from taskcat._dataclasses import Tag, TestRegion

LOG = logging.getLogger(__name__)

GENERIC_ERROR_PATTERNS = [
    r"(The following resource\(s\) failed to create: )",
    r"(^Resource creation cancelled$)",
]


def criteria_matches(criteria: dict, instance):
    # fail if criteria includes an invalid property
    for k in criteria:
        if k not in instance.__dict__:
            raise ValueError(f"{k} is not a valid property of {type(instance)}")
    for k, v in criteria.items():
        # matching is AND for multiple criteria, so as soon as one fails,
        # it's not a match
        if getattr(instance, k) != v:
            return False
    return True


class StackStatus:
    COMPLETE = ["CREATE_COMPLETE", "UPDATE_COMPLETE", "DELETE_COMPLETE"]
    IN_PROGRESS = [
        "CREATE_IN_PROGRESS",
        "DELETE_IN_PROGRESS",
        "UPDATE_IN_PROGRESS",
        "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS",
    ]
    FAILED = [
        "DELETE_FAILED",
        "CREATE_FAILED",
        "ROLLBACK_IN_PROGRESS",
        "ROLLBACK_FAILED",
        "ROLLBACK_COMPLETE",
        "UPDATE_ROLLBACK_IN_PROGRESS",
        "UPDATE_ROLLBACK_FAILED",
        "UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS",
        "UPDATE_ROLLBACK_COMPLETE",
        "OUT_OF_ORDER_EVENT",
    ]


class Capabilities:
    IAM = "CAPABILITY_IAM"
    NAMED_IAM = "CAPABILITY_NAMED_IAM"
    AUTO_EXPAND = "CAPABILITY_AUTO_EXPAND"
    ALL = [IAM, NAMED_IAM, AUTO_EXPAND]


class Event:
    def __init__(self, event_dict: dict):
        self.event_id: str = event_dict["EventId"]
        self.stack_name: str = event_dict["StackName"]
        self.logical_id: str = event_dict["LogicalResourceId"]
        self.type: str = event_dict["ResourceType"]
        self.status: str = event_dict["ResourceStatus"]
        self.physical_id: str = ""
        self.timestamp: datetime = datetime.fromtimestamp(0)
        self.status_reason: str = ""
        self.properties: dict = {}
        if "PhysicalResourceId" in event_dict.keys():
            self.physical_id = event_dict["PhysicalResourceId"]
        if "Timestamp" in event_dict.keys():
            self.timestamp = event_dict["Timestamp"]
        if "ResourceStatusReason" in event_dict.keys():
            self.status_reason = event_dict["ResourceStatusReason"]
        if "ResourceProperties" in event_dict.keys():
            self.properties = json.loads(event_dict["ResourceProperties"])

    def __str__(self):
        return "{} {} {}".format(self.timestamp, self.logical_id, self.status)

    def __repr__(self):
        return "<Event object {} at {}>".format(self.event_id, hex(id(self)))


class Resource:
    def __init__(
        self, stack_id: str, resource_dict: dict, test_name: str = "", uuid: UUID = None
    ):
        uuid = uuid if uuid else uuid4()
        self.stack_id: str = stack_id
        self.test_name: str = test_name
        self.uuid: UUID = uuid
        self.logical_id: str = resource_dict["LogicalResourceId"]
        self.type: str = resource_dict["ResourceType"]
        self.status: str = resource_dict["ResourceStatus"]
        self.physical_id: str = ""
        self.last_updated_timestamp: datetime = datetime.fromtimestamp(0)
        self.status_reason: str = ""
        if "PhysicalResourceId" in resource_dict.keys():
            self.physical_id = resource_dict["PhysicalResourceId"]
        if "LastUpdatedTimestamp" in resource_dict.keys():
            self.last_updated_timestamp = resource_dict["LastUpdatedTimestamp"]
        if "ResourceStatusReason" in resource_dict.keys():
            self.status_reason = resource_dict["ResourceStatusReason"]

    def __str__(self):
        return "<Resource {} {}>".format(self.logical_id, self.status)


class Parameter:
    def __init__(self, param_dict: dict):
        self.key: str = param_dict["ParameterKey"]
        self.value: str = ""
        self.raw_value: str = ""
        self.use_previous_value: bool = False
        self.resolved_value: str = ""
        if "ParameterValue" in param_dict.keys():
            self.value = param_dict["ParameterValue"]
        if "UsePreviousValue" in param_dict.keys():
            self.use_previous_value = param_dict["UsePreviousValue"]
        if "ResolvedValue" in param_dict.keys():
            self.resolved_value = param_dict["ResolvedValue"]
        if self.value and not self.raw_value:
            self.raw_value = self.value

    def dump(self):
        param_dict = {"ParameterKey": self.key}
        if self.value:
            param_dict["ParameterValue"] = self.value
        if self.use_previous_value:
            param_dict["UsePreviousValue"] = self.use_previous_value
        return param_dict


class Output:
    def __init__(self, output_dict: dict):
        self.key: str = output_dict["OutputKey"]
        self.value: str = output_dict["OutputValue"]
        self.description: str = ""
        self.export_name: str = ""
        if "Description" in output_dict.keys():
            self.description = output_dict["Description"]
        if "ExportName" in output_dict.keys():
            self.export_name = output_dict["ExportName"]


class FilterableList(list):
    def filter(self, criteria: Optional[dict] = None, **kwargs):
        if not criteria and not kwargs:
            return self
        if not criteria:
            criteria = kwargs
        flist = FilterableList()
        for item in self:
            if criteria_matches(criteria, item):
                flist.append(item)
        return flist


class Stacks(FilterableList):
    pass


class Resources(FilterableList):
    pass


class Events(FilterableList):
    pass


class Tags(FilterableList):
    pass


class Stack:  # pylint: disable=too-many-instance-attributes

    REMOTE_TEMPLATE_PATH = Path(".taskcat/.remote_templates")

    def __init__(
        self,
        region: TestRegion,
        stack_id: str,
        template: Template,
        test_name,
        uuid: UUID = None,
    ):
        uuid = uuid if uuid else uuid4()
        self.test_name: str = test_name
        self.uuid: UUID = uuid
        self.id: str = stack_id
        self.template: Template = template
        self.name: str = self._get_name()
        self.region: TestRegion = region
        self.region_name = region.name
        self.client: boto3.client = region.client("cloudformation")
        self.completion_time: timedelta = timedelta(0)
        self.role_arn = region.role_arn

        # properties from additional cfn api calls
        self._events: Events = Events()
        self._resources: Resources = Resources()
        self._children: Stacks = Stacks()
        # properties from describe_stacks response
        self.change_set_id: str = ""
        self.parameters: List[Parameter] = []
        self.creation_time: datetime = datetime.fromtimestamp(0)
        self.deletion_time: datetime = datetime.fromtimestamp(0)
        self._status: str = ""
        self.status_reason: str = ""
        self.disable_rollback: bool = False
        self.timeout_in_minutes: int = 0
        self.capabilities: List[str] = []
        self.outputs: List[Output] = []
        self.tags: List[Tag] = []
        self.parent_id: str = ""
        self.root_id: str = ""
        self._launch_succeeded: bool = False
        self._auto_refresh_interval: timedelta = timedelta(seconds=60)
        self._last_event_refresh: datetime = datetime.fromtimestamp(0)
        self._last_resource_refresh: datetime = datetime.fromtimestamp(0)
        self._last_child_refresh: datetime = datetime.fromtimestamp(0)
        self._timer = Timer(self._auto_refresh_interval.total_seconds(), self.refresh)
        self._timer.start()

    def __str__(self):
        return self.id

    def __repr__(self):
        return "<Stack object {} at {}>".format(self.name, hex(id(self)))

    def _get_region(self) -> str:
        return self.id.split(":")[3]

    def _get_name(self) -> str:
        return self.id.split(":")[5].split("/")[1]

    def _auto_refresh(self, last_refresh):
        if datetime.now() - last_refresh > self._auto_refresh_interval:
            return True
        return False

    @property
    def status(self):
        if self._status in StackStatus.COMPLETE:
            if not self.launch_succeeded:
                self._status = "OUT_OF_ORDER_EVENT"
                self.status_reason = (
                    "COMPLETE event not detected. "
                    + "Potential out-of-band action against the stack."
                )
        return self._status

    @status.setter
    def status(self, status):
        _complete = StackStatus.COMPLETE.copy()
        del _complete[_complete.index("DELETE_COMPLETE")]
        self._status = status
        if status in StackStatus.FAILED:
            self._launch_succeeded = False
            return
        if status in _complete:
            self._launch_succeeded = True
            return
        return

    @property
    def launch_succeeded(self):
        return self._launch_succeeded

    @classmethod
    def create(
        cls,
        region: TestRegion,
        stack_name: str,
        template: Template,
        tags: List[Tag] = None,
        disable_rollback: bool = True,
        test_name: str = "",
        uuid: UUID = None,
    ) -> "Stack":
        parameters = cls._cfn_format_parameters(region.parameters)
        uuid = uuid if uuid else uuid4()
        cfn_client = region.client("cloudformation")
        tags = [t.dump() for t in tags] if tags else []
        template = Template(
            template_path=template.template_path,
            project_root=template.project_root,
            s3_key_prefix=template.s3_key_prefix,
            url=s3_url_maker(
                region.s3_bucket.name,
                template.s3_key,
                region.client("s3"),
                region.s3_bucket.auto_generated,
            ),
            template_cache=tcat_template_cache,
        )
        create_options = {
            "StackName": stack_name,
            "TemplateURL": template.url,
            "Parameters": parameters,
            "DisableRollback": disable_rollback,
            "Tags": tags,
            "Capabilities": Capabilities.ALL,
        }
        if region.role_arn:
            create_options["RoleARN"] = region.role_arn
        stack_id = cfn_client.create_stack(**create_options)["StackId"]
        stack = cls(region, stack_id, template, test_name, uuid)
        # fetch property values from cfn
        stack.refresh()
        return stack

    @staticmethod
    def _cfn_format_parameters(parameters):
        return [{"ParameterKey": k, "ParameterValue": v} for k, v in parameters.items()]

    @classmethod
    def _import_child(  # pylint: disable=too-many-locals
        cls, stack_properties: dict, parent_stack: "Stack"
    ) -> Optional["Stack"]:
        try:
            url = ""
            for event in parent_stack.events():
                if (
                    event.physical_id == stack_properties["StackId"]
                    and event.properties
                ):
                    url = event.properties["TemplateURL"]
            if url.startswith(parent_stack.template.url_prefix()):
                # Template is part of the project, discovering path
                relative_path = url.replace(
                    parent_stack.template.url_prefix(), ""
                ).lstrip("/")
                absolute_path = parent_stack.template.project_root / relative_path
                if not absolute_path.is_file():
                    # try with the base folder stripped off
                    relative_path2 = Path(relative_path)
                    relative_path2 = relative_path2.relative_to(
                        *relative_path2.parts[:1]
                    )
                    absolute_path = parent_stack.template.project_root / relative_path2
                if not absolute_path.is_file():
                    LOG.warning(
                        f"Failed to find template for child stack "
                        f"{stack_properties['StackId']}. tried "
                        f"{parent_stack.template.project_root / relative_path}"
                        f" and {absolute_path}"
                    )
                    return None
            else:
                # Assuming template is remote to project and downloading it
                cfn_client = parent_stack.client
                tempate_body = cfn_client.get_template(
                    StackName=stack_properties["StackId"]
                )["TemplateBody"]
                path = parent_stack.template.project_root / Stack.REMOTE_TEMPLATE_PATH
                os.makedirs(path, exist_ok=True)
                fname = (
                    "".join(
                        random.choice(string.ascii_lowercase)  # nosec
                        for _ in range(16)
                    )
                    + ".template"
                )
                absolute_path = path / fname
                if not isinstance(tempate_body, str):
                    tempate_body = ordered_dump(tempate_body, dumper=yaml.SafeDumper)
                if not absolute_path.exists():
                    with open(absolute_path, "w") as fh:
                        fh.write(tempate_body)
            template = Template(
                template_path=str(absolute_path),
                project_root=parent_stack.template.project_root,
                url=url,
                template_cache=tcat_template_cache,
            )
            stack = cls(
                parent_stack.region,
                stack_properties["StackId"],
                template,
                parent_stack.name,
                parent_stack.uuid,
            )
            stack.set_stack_properties(stack_properties)
        except Exception as e:  # pylint: disable=broad-except
            LOG.warning(f"Failed to import child stack: {str(e)}")
            LOG.debug("traceback:", exc_info=True)
            return None
        return stack

    @classmethod
    def import_existing(
        cls,
        stack_properties: dict,
        template: Template,
        region: TestRegion,
        test_name: str,
        uid: UUID,
    ) -> "Stack":
        stack = cls(region, stack_properties["StackId"], template, test_name, uid)
        stack.set_stack_properties(stack_properties)
        return stack

    def refresh(
        self,
        properties: bool = True,
        events: bool = False,
        resources: bool = False,
        children: bool = False,
    ) -> None:
        if properties:
            self.set_stack_properties()
        if events:
            self._fetch_stack_events()
            self._last_event_refresh = datetime.now()
        if resources:
            self._fetch_stack_resources()
            self._last_resource_refresh = datetime.now()
        if children:
            self._fetch_children()
            self._last_child_refresh = datetime.now()

    def set_stack_properties(self, stack_properties: Optional[dict] = None) -> None:
        # TODO: get time to complete for complete stacks and % complete
        props: dict = stack_properties if stack_properties else {}
        self._timer.cancel()
        if not props:
            describe_stacks = self.client.describe_stacks
            props = describe_stacks(StackName=self.id)["Stacks"][0]
        iterable_props: List[Tuple[str, Callable]] = [
            ("Parameters", Parameter),
            ("Outputs", Output),
            ("Tags", Tag),
        ]
        for prop_name, prop_class in iterable_props:
            for item in props.get(prop_name, []):
                item = prop_class(item)
                self._merge_props(getattr(self, prop_name.lower()), item)
        for key, value in props.items():
            if key in [p[0] for p in iterable_props]:  # noqa: C412
                continue
            key = pascal_to_snake(key).replace("stack_", "")
            setattr(self, key, value)
        if self.status in StackStatus.IN_PROGRESS:
            self._timer = Timer(
                self._auto_refresh_interval.total_seconds(), self.refresh
            )
            self._timer.start()

    @staticmethod
    def _merge_props(existing_props, new):
        added = False
        for existing_id, prop in enumerate(existing_props):
            if prop.key == new.key:
                existing_props[existing_id] = new
                added = True
        if not added:
            existing_props.append(new)

    def events(self, refresh: bool = False, include_generic: bool = True) -> Events:
        if refresh or not self._events or self._auto_refresh(self._last_event_refresh):
            self._fetch_stack_events()
        events = self._events
        if not include_generic:
            events = Events([event for event in events if not self._is_generic(event)])
        return events

    @staticmethod
    def _is_generic(event: Event) -> bool:
        generic = False
        for regex in GENERIC_ERROR_PATTERNS:
            if re.search(regex, event.status_reason):
                generic = True
        return generic

    def _fetch_stack_events(self) -> None:
        self._last_event_refresh = datetime.now()
        events = Events()
        for page in self.client.get_paginator("describe_stack_events").paginate(
            StackName=self.id
        ):
            for event in page["StackEvents"]:
                events.append(Event(event))
        self._events = events

    def resources(self, refresh: bool = False) -> Resources:
        if (
            refresh
            or not self._resources
            or self._auto_refresh(self._last_resource_refresh)
        ):
            self._fetch_stack_resources()
        return self._resources

    def _fetch_stack_resources(self) -> None:
        self._last_resource_refresh = datetime.now()
        resources = Resources()
        for page in self.client.get_paginator("list_stack_resources").paginate(
            StackName=self.id
        ):
            for resource in page["StackResourceSummaries"]:
                resources.append(Resource(self.id, resource, self.test_name, self.uuid))
        self._resources = resources

    @staticmethod
    def delete(client, stack_id) -> None:
        client.delete_stack(StackName=stack_id)
        LOG.info(f"Deleting stack: {stack_id}")

    def update(self, *args, **kwargs):
        raise NotImplementedError("Stack updates not implemented")

    def _fetch_children(self) -> None:
        self._last_child_refresh = datetime.now()
        for page in self.client.get_paginator("describe_stacks").paginate():
            for stack in page["Stacks"]:
                if self._children.filter(id=stack["StackId"]):
                    continue
                if "ParentId" in stack.keys():
                    if self.id == stack["ParentId"]:
                        stack_obj = Stack._import_child(stack, self)
                        if stack_obj:
                            self._children.append(stack_obj)

    def children(self, refresh=False) -> Stacks:
        if (
            refresh
            or not self._children
            or self._auto_refresh(self._last_child_refresh)
        ):
            self._fetch_children()
        return self._children

    def descendants(self, refresh=False) -> Stacks:
        if refresh or not self._children:
            self._fetch_children()

        def recurse(stack: Stack, descendants: Stacks = None) -> Stacks:
            descendants = descendants if descendants else Stacks()
            if stack.children(refresh=refresh):
                descendants += stack.children()
                for child in stack.children():
                    descendants = recurse(child, descendants)
            return descendants

        return recurse(self)

    def error_events(
        self, recurse: bool = True, include_generic: bool = False, refresh=False
    ) -> Events:
        errors = Events()
        stacks = Stacks([self])
        if recurse:
            stacks += self.descendants()
        for stack in stacks:
            for status in StackStatus.FAILED:
                errors += stack.events(
                    refresh=refresh, include_generic=include_generic
                ).filter({"status": status})
        return errors
