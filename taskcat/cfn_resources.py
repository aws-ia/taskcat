import sys
from taskcat.colored_console import PrintMsg
from taskcat.common_utils import CommonTools
from taskcat.exceptions import TaskCatException


class CfnResourceTools:
    def __init__(self, boto_client):
        self._boto_client = boto_client

    def get_resources(self, stackname, region, include_stacks=False):
        """
        Given a stackname, and region function returns the list of dictionary items, where each item
        consist of logicalId, physicalId and resourceType of the aws resource associated
        with the stack.

        :param include_stacks:
        :param stackname: CloudFormation stack name
        :param region: AWS region
        :return: List of objects in the following format
             [
                 {
                     'logicalId': 'string',
                     'physicalId': 'string',
                     'resourceType': 'String'
                 },
             ]

        """
        l_resources = []
        self.get_resources_helper(stackname, region, l_resources, include_stacks)
        return l_resources

    def get_resources_helper(self, stackname, region, l_resources, include_stacks):
        """
        This is a helper function of get_resources function. Check get_resources function for details.

        """
        if stackname != 'None':
            try:
                cfn = self._boto_client.get('cloudformation', region=region)
                result = cfn.describe_stack_resources(StackName=stackname)
                stack_resources = result.get('StackResources')
                for resource in stack_resources:
                    print(PrintMsg.INFO + "Resources: for {}".format(stackname))
                    print(PrintMsg.INFO + "{0} = {1}, {2} = {3}, {4} = {5}".format(
                        '\n\t\tLogicalId',
                        resource.get('LogicalResourceId'),
                        '\n\t\tPhysicalId',
                        resource.get('PhysicalResourceId'),
                        '\n\t\tType',
                        resource.get('ResourceType')
                        ))
                    # if resource is a stack and has a physical resource id
                    # (NOTE: physical id will be missing if stack creation is failed)
                    if resource.get(
                            'ResourceType') == 'AWS::CloudFormation::Stack' and 'PhysicalResourceId' in resource:
                        if include_stacks:
                            d = {'logicalId': resource.get('LogicalResourceId'),
                                 'physicalId': resource.get('PhysicalResourceId'),
                                 'resourceType': resource.get('ResourceType')}
                            l_resources.append(d)
                        stackdata = CommonTools(str(resource.get('PhysicalResourceId'))).parse_stack_info()
                        region = stackdata['region']
                        self.get_resources_helper(resource.get('PhysicalResourceId'), region, l_resources,
                                                  include_stacks)
                    # else if resource is not a stack and has a physical resource id
                    # (NOTE: physical id will be missing if stack creation is failed)
                    elif resource.get(
                            'ResourceType') != 'AWS::CloudFormation::Stack' and 'PhysicalResourceId' in resource:
                        d = {'logicalId': resource.get('LogicalResourceId'),
                             'physicalId': resource.get('PhysicalResourceId'),
                             'resourceType': resource.get('ResourceType')}
                        l_resources.append(d)
            except TaskCatException:
                raise
            except Exception as e:
                print(PrintMsg.ERROR + str(e))
                raise TaskCatException("Unable to get resources for stack %s" % stackname)

    def get_all_resources(self, stackids, region):
        """
        Given a list of stackids, function returns the list of dictionary items, where each
        item consist of stackId and the resources associated with that stack.

        :param stackids: List of Stack Ids
        :param region: AWS region
        :return: A list of dictionary object in the following format
                [
                    {
                        'stackId': 'string',
                        'resources': [
                            {
                               'logicalId': 'string',
                               'physicalId': 'string',
                               'resourceType': 'String'
                            },
                        ]
                    },
                ]

        """
        l_all_resources = []
        for anId in stackids:
            d = {
                'stackId': anId,
                'resources': self.get_resources(anId, region)
            }
            l_all_resources.append(d)
        return l_all_resources