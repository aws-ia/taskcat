from uuid import UUID, uuid4
from taskcat.client_factory import ClientFactory
from datetime import datetime
from typing import List
import re
from taskcat.cfn.template import Template
import json
import os
from pathlib import Path
import random
import string

GENERIC_ERROR_PATTERNS = [
    r'(The following resource\(s\) failed to create: )',
    r'(^Resource creation cancelled$)'
]


class StackStatus:
    COMPLETE = ['CREATE_COMPLETE', 'UPDATE_COMPLETE', 'DELETE_COMPLETE']
    IN_PROGRESS = ['CREATE_IN_PROGRESS', 'DELETE_IN_PROGRESS', 'UPDATE_IN_PROGRESS',
                   'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS']
    FAILED = ['DELETE_FAILED', 'CREATE_FAILED', 'ROLLBACK_IN_PROGRESS', 'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE',
              'UPDATE_ROLLBACK_IN_PROGRESS''UPDATE_ROLLBACK_FAILED', 'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
              'UPDATE_ROLLBACK_COMPLETE']


class Capabilities:
    IAM = 'CAPABILITY_IAM'
    NAMED_IAM = 'CAPABILITY_NAMED_IAM'
    AUTO_EXPAND = 'CAPABILITY_AUTO_EXPAND'
    ALL = [IAM, NAMED_IAM, AUTO_EXPAND]


class Event:
    def __init__(self, event_dict: dict, test_name: str = '', uuid: UUID = uuid4()):
        self.stack_id: str = event_dict['StackId']
        self.test_name: str = test_name
        self.uuid: UUID = uuid
        self.event_id: str = event_dict['EventId']
        self.stack_name: str = event_dict['StackName']
        self.logical_id: str = event_dict['LogicalResourceId']
        self.type: str = event_dict['ResourceType']
        self.status: str = event_dict['ResourceStatus']
        self.physical_id: str = ''
        self.timestamp: datetime = datetime.fromtimestamp(0)
        self.status_reason: str = ''
        self.properties: dict = {}
        if 'PhysicalResourceId' in event_dict.keys():
            self.physical_id = event_dict['PhysicalResourceId']
        if 'Timestamp' in event_dict.keys():
            self.timestamp = event_dict['Timestamp']
        if 'ResourceStatusReason' in event_dict.keys():
            self.status_reason = event_dict['ResourceStatusReason']
        if 'ResourceProperties' in event_dict.keys():
            self.properties = json.loads(event_dict['ResourceProperties'])

    def __str__(self):
        return "{} {} {}".format(self.timestamp, self.logical_id, self.status)

    def __repr__(self):
        return "<Event object {} at {}>".format(self.event_id, hex(id(self)))


class Resource:
    def __init__(self, stack_id: str, resource_dict: dict, test_name: str = '', uuid: UUID = uuid4()):
        self.stack_id: str = stack_id
        self.test_name: str = test_name
        self.uuid: UUID = uuid
        self.logical_id: str = resource_dict['LogicalResourceId']
        self.type: str = resource_dict['ResourceType']
        self.status: str = resource_dict['ResourceStatus']
        self.physical_id: str = ''
        self.last_updated_timestamp: datetime = datetime.fromtimestamp(0)
        self.status_reason: str = ''
        if 'PhysicalResourceId' in resource_dict.keys():
            self.physical_id = resource_dict['PhysicalResourceId']
        if 'LastUpdatedTimestamp' in resource_dict.keys():
            self.last_updated_timestamp = resource_dict['LastUpdatedTimestamp']
        if 'ResourceStatusReason' in resource_dict.keys():
            self.status_reason = resource_dict['ResourceStatusReason']

    def __str__(self):
        return "<Resource {} {}>".format(self.logical_id, self.status)


class Parameter:
    def __init__(self, param_dict: dict):
        self.key: str = param_dict['ParameterKey']
        self.value: str = ''
        self.use_previous_value: bool = False
        self.resolved_value: str = ''
        if 'ParameterValue' in param_dict.keys():
            self.value = param_dict['ParameterValue']
        if 'UsePreviousValue' in param_dict.keys():
            self.use_previous_value = param_dict['UsePreviousValue']
        if 'ResolvedValue' in param_dict.keys():
            self.resolved_value = param_dict['ResolvedValue']

    def dump(self):
        param_dict = {
            'ParameterKey': self.key
        }
        if self.value:
            param_dict['ParameterValue'] = self.value
        if self.use_previous_value:
            param_dict['UsePreviousValue'] = self.use_previous_value
        return param_dict


class Output:
    def __init__(self, output_dict: dict):
        self.key: str = output_dict['OutputKey']
        self.value: str = output_dict['OutputValue']
        self.description: str = ''
        self.export_name: str = ''
        if 'Description' in output_dict.keys():
            self.description = output_dict['Description']
        if 'ExportName' in output_dict.keys():
            self.export_name: str = output_dict['ExportName']


class Tag:
    def __init__(self, tag_dict: dict):
        self.key: str = tag_dict['Key']
        self.value: str = tag_dict['Value']

    def dump(self):
        tag_dict = {
            'Key': self.key,
            'Value': self.value
        }
        return tag_dict


class Stack:

    REMOTE_TEMPLATE_PATH = Path('.taskcat/.remote_templates')

    def __init__(self, stack_id: str, template: Template, test_name: str = '', uuid: UUID = uuid4(),
                 client_factory_instance: ClientFactory = ClientFactory()):
        self.test_name: str = test_name
        self.uuid: UUID = uuid
        self.id: str = stack_id
        self.template: Template = template
        self.name: str = self._get_name()
        self.region: str = self._get_region()
        self._get_client: ClientFactory = client_factory_instance
        # properties from additional cfn api calls
        self._events: List[Event] = []
        self._resources: List[Resource] = []
        self._children: List[Stack] = []
        # properties from describe_stacks response
        self.change_set_id: str = ''
        self.parameters: List[Parameter] = []
        self.creation_time: datetime = datetime.fromtimestamp(0)
        self.deletion_time: datetime = datetime.fromtimestamp(0)
        self.status: str = ''
        self.status_reason: str = ''
        self.disable_rollback: bool = False
        self.timeout_in_minutes: int = 0
        self.capabilities: List[str] = []
        self.outputs: List[Output] = []
        self.tags: List[Tag] = []
        self.parent_id: str = ''
        self.root_id: str = ''

    def __str__(self):
        return self.id

    def __repr__(self):
        return "<Stack object {} at {}>".format(self.name, hex(id(self)))

    def _get_region(self) -> str:
        return self.id.split(':')[3]

    def _get_name(self) -> str:
        return self.id.split(':')[5].split('/')[1]

    @classmethod
    def create(cls, stack_name: str, template: Template, region: str, parameters: List[Parameter] = None,
               tags: List[Tag] = None, disable_rollback: bool = True, test_name: str = '', uuid: UUID = uuid4(),
               client_factory_instance: ClientFactory = ClientFactory()) -> 'Stack':
        cfn_client = client_factory_instance.get('cloudformation', region=region)
        parameters = [p.dump() for p in parameters] if parameters else []
        tags = [t.dump() for t in tags] if tags else []
        stack_id = cfn_client.create_stack(
            StackName=stack_name, TemplateURL=template.url, Parameters=parameters, DisableRollback=disable_rollback,
            Tags=tags, Capabilities=Capabilities.ALL)['StackId']
        stack = cls(stack_id, template, test_name, uuid, client_factory_instance)
        # fetch property values from cfn
        stack.refresh()

        return stack

    @classmethod
    def import_from_properties(cls, stack_properties: dict, parent_stack: 'Stack') -> 'Stack':
        url = ''
        for event in parent_stack.events():
            if event.physical_id == stack_properties['StackId'] and event.properties:
                url = event.properties['TemplateURL']
        if url.startswith(parent_stack.template.url_prefix()):
            # Template is part of the project, discovering path
            relative_path = url.replace(parent_stack.template.url_prefix(), '').lstrip('/')
            absolute_path = parent_stack.template.project_root / relative_path
        else:
            # Assuming template is remote to project and downloading it
            cfn_client = parent_stack._get_client.get('cloudformation', region=parent_stack.region)
            tempate_body = cfn_client.get_template(StackName=stack_properties['StackId'])['TemplateBody']
            path = parent_stack.template.project_root / Stack.REMOTE_TEMPLATE_PATH
            os.makedirs(path, exist_ok=True)
            fname = ''.join(random.choice(string.ascii_lowercase) for _ in range(16)) + '.template'
            absolute_path = path / fname
            with open(absolute_path, 'w') as fh:
                fh.write(tempate_body)
        template = Template(str(absolute_path), parent_stack.template.project_root, url, parent_stack._get_client)
        stack = cls(stack_properties['StackId'], template, parent_stack.name, parent_stack.uuid,
                    parent_stack._get_client)
        stack._set_stack_properties(stack_properties)
        return stack

    def refresh(self, properties: bool = True, events: bool = False, resources: bool = False, children: bool = False) -> None:
        if properties:
            self._set_stack_properties()
        if events:
            self._fetch_stack_events()
        if resources:
            self._fetch_stack_resources()
        if children:
            self._fetch_children()

    def _set_stack_properties(self, stack_properties: dict = None) -> None:
        if not stack_properties:
            cfn_client = self._get_client.get('cloudformation', region=self.region)
            stack_properties = cfn_client.describe_stacks(StackName=self.id)["Stacks"][0]
        if 'Parameters' in stack_properties.keys():
            for param in stack_properties['Parameters']:
                self.parameters.append(Parameter(param))
        if 'Outputs' in stack_properties.keys():
            for outp in stack_properties['Outputs']:
                self.outputs.append(Output(outp))
        if 'Tags' in stack_properties.keys():
            for tag in stack_properties['Tags']:
                self.tags.append(Tag(tag))
        if 'ChangeSetId' in stack_properties.keys():
            self.change_set_id = stack_properties['ChangeSetId']
        if 'CreationTime' in stack_properties.keys():
            self.creation_time = stack_properties['CreationTime']
        if 'DeletionTime' in stack_properties.keys():
            self.deletion_time = stack_properties['DeletionTime']
        if 'StackStatus' in stack_properties.keys():
            self.status = stack_properties['StackStatus']
        if 'StackStatusReason' in stack_properties.keys():
            self.status_reason = stack_properties['StackStatusReason']
        if 'DisableRollback' in stack_properties.keys():
            self.disable_rollback = stack_properties['DisableRollback']
        if 'TimeoutInMinutes' in stack_properties.keys():
            self.timeout_in_minutes = stack_properties['TimeoutInMinutes']
        if 'Capabilities' in stack_properties.keys():
            self.capabilities = stack_properties['Capabilities']
        if 'ParentId' in stack_properties.keys():
            self.parent_id = stack_properties['ParentId']
        if 'RootId' in stack_properties.keys():
            self.root_id = stack_properties['RootId']

    def events(self, filter_status: [str] = None, refresh: bool = False, include_generic: bool = True) -> List[Event]:
        if refresh or not self._events:
            self._fetch_stack_events()
        events = self._events
        if filter_status:
            events = [event for event in self._events if event.status in filter_status]
        if not include_generic:
            events = [event for event in events if not self._is_generic(event)]
        return events

    @staticmethod
    def _is_generic(event: Event) -> bool:
        generic = False
        for regex in GENERIC_ERROR_PATTERNS:
            if re.search(regex, event.status_reason):
                generic = True
        return generic

    def _fetch_stack_events(self) -> None:
        cfn_client = self._get_client.get('cloudformation', region=self.region)
        events = []
        for page in cfn_client.get_paginator('describe_stack_events').paginate(StackName=self.id):
            for event in page["StackEvents"]:
                events.append(Event(event))
        self._events = events

    def resources(self, filter_status: [str] = None, refresh: bool = False) -> List[Resource]:
        if refresh or not self._resources:
            self._fetch_stack_resources()
        if filter_status:
            return [resource for resource in self._resources if resource.status in filter_status]
        return self._resources

    def _fetch_stack_resources(self) -> None:
        cfn_client = self._get_client.get('cloudformation', region=self.region)
        resources = []
        for page in cfn_client.get_paginator('list_stack_resources').paginate(StackName=self.id):
            for resource in page['StackResourceSummaries']:
                resources.append(Resource(self.id, resource, self.test_name, self.uuid))
        self._resources = resources

    def delete(self) -> None:
        cfn_client = self._get_client.get('cloudformation', region=self.region)
        cfn_client.delete_stack(StackName=self.id)

    def update(self, * args, **kwargs):
        raise NotImplementedError("Stack updates not implemented")

    def _fetch_children(self) -> None:
        cfn_client = self._get_client.get('cloudformation', region=self.region)
        for page in cfn_client.get_paginator('describe_stacks').paginate():
            for stack in page['Stacks']:
                if 'ParentId' in stack.keys():
                    if self.id == stack['ParentId']:
                        stack_obj = Stack.import_from_properties(stack, self)
                        self._children.append(stack_obj)

    def children(self, refresh=False) -> List['Stack']:
        if refresh or not self._children:
            self._fetch_children()
        return self._children

    def descendants(self, refresh=False) -> List['Stack']:
        if refresh or not self._children:
            self._fetch_children()

        def recurse(stack: Stack, descendants: List['Stack'] = []) -> ['Stack']:
            if stack.children():
                descendants += stack.children()
                for child in stack.children():
                    descendants = recurse(child, descendants)
            return descendants

        return recurse(self)

    def error_events(self, recurse: bool = True, include_generic: bool = False, refresh=False) -> [Event]:
        errors = []
        stacks = [self]
        if recurse:
            stacks += self.descendants()
        for stack in stacks:
            errors += stack.events(refresh=refresh, filter_status=StackStatus.FAILED, include_generic=include_generic)
        return errors
