# TODO: refactor
import datetime
import logging
import textwrap
from pathlib import Path
from typing import List

import tabulate

from .stack import Event, Stack
from .threaded import Stacker

LOG = logging.getLogger(__name__)


class _CfnLogTools:
    def __init__(self):
        pass

    @staticmethod
    def get_cfn_stack_events(stack: Stack) -> List[Event]:
        return stack.events(refresh=True)

    def get_cfnlogs(self, stack: Stack):
        # Collect stack_events
        stack_events = self.get_cfn_stack_events(stack)
        events = []
        for event in stack_events:
            event_details = {
                "TimeStamp": str(event.timestamp),
                "ResourceStatus": event.status,
                "ResourceType": event.type,
                "LogicalResourceId": event.logical_id,
            }
            if event.status_reason:
                event_details["ResourceStatusReason"] = event.status_reason
            else:
                event_details["ResourceStatusReason"] = ""

            events.append(event_details)

        return events

    def createcfnlogs(self, stacks: Stacker, logpath: Path):
        for stack in stacks.stacks:
            stackname = stack.name
            region = stack.region_name
            extension = ".txt"
            test_logpath = logpath / "{}-{}-{}{}".format(
                stackname, region, "cfnlogs", extension
            )
            self.write_logs(stack, test_logpath)

    def write_logs(self, stack: Stack, logpath: Path):
        stackname = stack.name
        region = stack.region_name

        # Get stack resources
        cfnlogs = self.get_cfnlogs(stack)

        if len(cfnlogs) != 0:
            if cfnlogs[0]["ResourceStatus"] != "CREATE_COMPLETE":
                if "ResourceStatusReason" in cfnlogs[0]:
                    reason = cfnlogs[0]["ResourceStatusReason"]
                else:
                    reason = "Unknown"
            else:
                reason = "Stack launch was successful"

            with open(str(logpath), "a") as log_output:
                log_output.write(
                    "------------------------------------------------------------------"
                    "-----------\n"
                )
                log_output.write("Region: " + region + "\n")
                log_output.write("StackName: " + stackname + "\n")
                log_output.write(
                    "******************************************************************"
                    "***********\n"
                )
                log_output.write("ResourceStatusReason:  \n")
                log_output.write(textwrap.fill(str(reason), 85) + "\n")
                log_output.write(
                    "******************************************************************"
                    "***********\n"
                )
                log_output.write(
                    "******************************************************************"
                    "***********\n"
                )
                log_output.write("Events:  \n")
                log_output.writelines(tabulate.tabulate(cfnlogs, headers="keys"))
                log_output.write(
                    "\n****************************************************************"
                    "*************\n"
                )
                log_output.write(
                    "------------------------------------------------------------------"
                    "-----------\n"
                )
                log_output.write(
                    "Tested on: "
                    + datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")
                    + "\n"
                )
                log_output.write(
                    "------------------------------------------------------------------"
                    "-----------\n\n"
                )
                log_output.close()

            for child in stack.descendants(refresh=True):
                self.write_logs(child, logpath)
        else:
            LOG.error(
                "No event logs found. Something went wrong at describe event " "call."
            )
