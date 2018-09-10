import datetime
import textwrap
import tabulate
from botocore.exceptions import ClientError

from taskcat.colored_console import PrintMsg
from taskcat.common_utils import CommonTools
from taskcat.cfn_resources import CfnResourceTools


class CfnLogTools:
    def __init__(self, boto_client):
        self._boto_client = boto_client

    def get_cfn_stack_events(self, stackname, region):
        """
        Given a stack name and the region, this function returns the event logs of the given stack, as list.
        :param self:
        :param stackname: Name of the stack
        :param region: Region stack belongs to
        :return: Event logs of the stack
        """
        cfn_client = self._boto_client.get('cloudformation', region)
        stack_events = []
        try:
            response = cfn_client.describe_stack_events(StackName=stackname)
            stack_events.extend(response['StackEvents'])
            while 'NextToken' in response:
                response = cfn_client.describe_stack_events(NextToken=response['NextToken'], StackName=stackname)
                stack_events.extend(response['StackEvents'])
        except ClientError as e:
            print("{} Error trying to get the events for stack [{}] in region [{}]\b {}".format(
                PrintMsg.ERROR,
                str(stackname),
                str(region),
                e
            ))
            # Commenting below line to avoid sudden exit on describe call failure. So that delete stack may continue.
            # sys.exit()

        return stack_events

    def get_cfnlogs(self, stackname, region):
        """
        This function returns the event logs of the given stack in a specific format.
        :param stackname: Name of the stack
        :param region: Region stack belongs to
        :return: Event logs of the stack
        """

        print(PrintMsg.INFO + "Collecting logs for " + stackname + "\"\n")
        # Collect stack_events
        stack_events = self.get_cfn_stack_events(stackname, region)
        # Uncomment line for debug
        # pprint.pprint (stack_events)
        events = []
        for event in stack_events:
            event_details = {'TimeStamp': event['Timestamp'],
                             'ResourceStatus': event['ResourceStatus'],
                             'ResourceType': event['ResourceType'],
                             'LogicalResourceId': event['LogicalResourceId']}
            if 'ResourceStatusReason' in event:
                event_details['ResourceStatusReason'] = event['ResourceStatusReason']
            else:
                event_details['ResourceStatusReason'] = ''

            events.append(event_details)

        return events

    def createcfnlogs(self, testdata_list, logpath):
        """
        This function creates the CloudFormation log files.

        :param testdata_list: List of TestData objects
        :param logpath: Log file path
        :return:
        """
        print("{}Collecting CloudFormation Logs".format(PrintMsg.INFO))
        for test in testdata_list:
            for stack in test.get_test_stacks():
                stackinfo = CommonTools(stack['StackId']).parse_stack_info()
                stackname = str(stackinfo['stack_name'])
                region = str(stackinfo['region'])
                extension = '.txt'
                test_logpath = '{}/{}-{}-{}{}'.format(
                    logpath,
                    stackname,
                    region,
                    'cfnlogs',
                    extension)
                self.write_logs(str(stack['StackId']), test_logpath)

    def write_logs(self, stack_id, logpath):
        """
        This function writes the event logs of the given stack and all the child stacks to a given file.
        :param stack_id: Stack Id
        :param logpath: Log file path
        :return:
        """
        stackinfo = CommonTools(stack_id).parse_stack_info()
        stackname = str(stackinfo['stack_name'])
        region = str(stackinfo['region'])

        # Get stack resources
        cfnlogs = self.get_cfnlogs(stackname, region)

        if len(cfnlogs) != 0:
            if cfnlogs[0]['ResourceStatus'] != 'CREATE_COMPLETE':
                if 'ResourceStatusReason' in cfnlogs[0]:
                    reason = cfnlogs[0]['ResourceStatusReason']
                else:
                    reason = 'Unknown'
            else:
                reason = "Stack launch was successful"

            print("\t |StackName: " + stackname)
            print("\t |Region: " + region)
            print("\t |Logging to: " + logpath)
            print("\t |Tested on: " + str(datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")))
            print("------------------------------------------------------------------------------------------")
            print("ResourceStatusReason: ")
            print(textwrap.fill(str(reason), 85))
            print("==========================================================================================")
            with open(logpath, "a") as log_output:
                log_output.write("-----------------------------------------------------------------------------\n")
                log_output.write("Region: " + region + "\n")
                log_output.write("StackName: " + stackname + "\n")
                log_output.write("*****************************************************************************\n")
                log_output.write("ResourceStatusReason:  \n")
                log_output.write(textwrap.fill(str(reason), 85) + "\n")
                log_output.write("*****************************************************************************\n")
                log_output.write("*****************************************************************************\n")
                log_output.write("Events:  \n")
                log_output.writelines(tabulate.tabulate(cfnlogs, headers="keys"))
                log_output.write(
                    "\n*****************************************************************************\n")
                log_output.write("-----------------------------------------------------------------------------\n")
                log_output.write("Tested on: " + datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p") + "\n")
                log_output.write(
                    "-----------------------------------------------------------------------------\n\n")
                log_output.close()

            # Collect resources of the stack and get event logs for any child stacks
            resources = CfnResourceTools(self._boto_client).get_resources(stackname,
                                                                          region,
                                                                          include_stacks=True)
            for resource in resources:
                if resource['resourceType'] == 'AWS::CloudFormation::Stack':
                    self.write_logs(resource['physicalId'], logpath)
        else:
            print(PrintMsg.ERROR + "No event logs found. Something went wrong at describe event call.\n")
