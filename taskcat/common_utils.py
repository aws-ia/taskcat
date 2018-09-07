import re


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

        :param stack_name: Full stack name arn
        :return: Dictionary object containing the region and stack name

        """
        stack_info = dict()
        region_re = re.compile('(?<=:)(.\w-.+(\w*)-\d)(?=:)')
        stack_name_re = re.compile('(?<=:stack/)(tCaT.*.)(?=/)')
        stack_info['region'] = self.regxfind(region_re, self.stack_name)
        stack_info['stack_name'] = self.regxfind(stack_name_re, self.stack_name)
        return stack_info
