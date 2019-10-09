import logging
import time

from reprint import output
from taskcat._cfn.threaded import Stacker as TaskcatStacker
from taskcat._logger import PrintMsg

LOG = logging.getLogger(__name__)


class TerminalPrinter:
    def __init__(self):
        self._buffer_type = "list"
        self.buffer = self._add_buffer()

    def _add_buffer(self):
        with output(output_type=self._buffer_type) as output_buffer:
            return output_buffer

    def report_test_progress(self, stacker: TaskcatStacker, poll_interval=10):
        _status_dict = stacker.status()
        while self._is_test_in_progress(_status_dict):
            for stack in stacker.stacks:
                self._print_stack_tree(stack, buffer=self.buffer)
            time.sleep(poll_interval)
            self.buffer.clear()
            _status_dict = stacker.status()

        self._display_final_status(stacker)

    @staticmethod
    def _print_stack_tree(stack, buffer):
        padding_1 = "         "
        buffer.append(
            "{}{}stack {} {}".format(padding_1, "\u250f ", "\u24c2", stack.name)
        )
        if stack.descendants():
            for nested_stack in stack.descendants():
                buffer.append(
                    "{}{}stack {} {}".format(
                        padding_1, "\u2523 ", "\u24c3", nested_stack.name
                    )
                )
        buffer.append("{}{} region: {}".format(padding_1, "\u2523", stack.region_name))
        buffer.append(
            "{}{}status: {}{}{}".format(
                padding_1, "\u2517 ", PrintMsg.white, stack.status, PrintMsg.rst_color
            )
        )

    @staticmethod
    def _display_final_status(stacker: TaskcatStacker):
        for final_stack in stacker.stacks:
            LOG.info("{}stack {} {}".format("\u250f ", "\u24c2", final_stack.name))
            if final_stack.descendants():
                for nested_stack in final_stack.descendants():
                    LOG.info(
                        "{}stack {} {}".format("\u2523 ", "\u24c3", nested_stack.name)
                    )
            LOG.info("{} region: {}".format("\u2523", final_stack.region_name))

            LOG.info(
                "{}status: {}{} {}".format(
                    "\u2517 ", PrintMsg.white, final_stack.status, PrintMsg.rst_color
                )
            )

    @staticmethod
    def _is_test_in_progress(status_dict, status_condition="IN_PROGRESS"):
        return bool(len(status_dict[status_condition]) > 0)
