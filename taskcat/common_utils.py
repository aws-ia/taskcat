import re
import sys
import os
from taskcat.colored_console import PrintMsg
from taskcat.exceptions import TaskCatException


class CommonTools:

    def __init__(self, stack_name):
        self.stack_name = stack_name

    def regxfind(self, re_object, data_line):
        """
        Returns the matching string.

        :param re_object: Regex object
        :param data_line: String to be searched

        :return: Matching String if found, otherwise return 'Not-found'
        """
        sg = re_object.search(data_line)
        if sg:
            return str(sg.group())
        else:
            return str('Not-found')

    def parse_stack_info(self):
        """
        Returns a dictionary object containing the region and stack name.

        :return: Dictionary object containing the region and stack name

        """
        stack_info = dict()
        region_re = re.compile('(?<=:)(.\w-.+(\w*)-\d)(?=:)')
        stack_name_re = re.compile('(?<=:stack/)(tCaT.*.)(?=/)')
        stack_info['region'] = self.regxfind(region_re, self.stack_name)
        stack_info['stack_name'] = self.regxfind(stack_name_re, self.stack_name)
        return stack_info


def exit1(msg=''):
    if msg:
        print(PrintMsg.ERROR + msg)
    sys.exit(1)


def exit0(msg=''):
    if msg:
        print(PrintMsg.INFO + msg)
    sys.exit(0)


def make_dir(path, ignore_exists=True):
    path = os.path.abspath(path)
    if ignore_exists and os.path.isdir(path):
        return
    os.makedirs(path)


def param_list_to_dict(original_keys):
    # Setup a list index dictionary.
    # - Used to give an Parameter => Index mapping for replacement.
    param_index = {}
    if type(original_keys) != list:
        raise TaskCatException('Invalid parameter file, outermost json element must be a list ("[]")')
    for (idx, param_dict) in enumerate(original_keys):
        if type(param_dict) != dict:
            raise TaskCatException('Invalid parameter %s parameters must be of type dict ("{}")' % param_dict)
        if 'ParameterKey' not in param_dict or 'ParameterValue' not in param_dict:
            raise TaskCatException(
                'Invalid parameter %s all items must have both ParameterKey and ParameterValue keys' % param_dict)
        key = param_dict['ParameterKey']
        param_index[key] = idx
    return param_index