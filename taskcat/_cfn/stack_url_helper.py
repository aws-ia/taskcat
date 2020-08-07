"""
  Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Permission is hereby granted, free of charge, to any person obtaining a copy of this
  software and associated documentation files (the "Software"), to deal in the Software
  without restriction, including without limitation the rights to use, copy, modify,
  merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
  INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
  PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

LOG = logging.getLogger(__name__)


class StackURLHelper:
    MAX_DEPTH = 20  # Handle at most 20 levels of nesting in TemplateURL expressions
    # TODO: Allow user to inject this
    # SUBSTITUTION = {
    #     "QSS3BucketName": "aws-quickstart",
    #     "QSS3KeyPrefix": "QSS3KeyPrefix/",
    #     "qss3KeyPrefix": "qss3KeyPrefix/",
    #     "AWS::Region": "us-east-1",
    #     "AWS::AccountId": "8888XXXX9999",
    # }

    SUBSTITUTION = {
        "AWS::Region": "us-east-1",
        "AWS::URLSuffix": "amazonaws.com",
        "AWS::AccountId": "8888XXXX9999",
    }

    def __init__(
        self, template_mappings=None, template_parameters=None, parameter_values=None,
    ):
        if template_mappings:
            self.mappings = template_mappings
        else:
            self.mappings = {}

        if template_parameters:
            self.template_parameters = template_parameters
        else:
            self.template_parameters = {}

        if parameter_values:
            self.parameter_values = parameter_values
        else:
            self.parameter_values = {}

        default_parameters: dict = {}
        for parameter in self.template_parameters:
            properties = self.template_parameters.get(parameter)
            if "Default" in properties.keys():
                default_parameters[parameter] = properties["Default"]

        self.SUBSTITUTION.update(default_parameters)
        self.SUBSTITUTION.update(self.parameter_values)

    def rewrite_vars(self, original_string, depth=1):
        """Replace the ${var} placeholders with ##var##"""
        parts = original_string.split("${")
        parts = parts[1].split("}")

        rep_text = "${" + parts[0] + "}"
        rep_with = "##" + parts[0] + "##"

        result = original_string.replace(rep_text, rep_with)

        if len(result.split("${")) > 1:
            result = self.rewrite_vars(result, depth=(depth + 1))

        return result

    def rewrite_sub_vars(self, original_string, depth=1):
        """Replace the '##var##' placeholders with 'var'"""
        if "##" not in original_string:
            return original_string

        parts = original_string.split("##")
        parts = parts[1].split("##")

        rep_text = "##" + parts[0] + "##"
        rep_with = "" + parts[0] + ""

        result = original_string.replace(rep_text, rep_with)

        if "##" in result:  # Recurse if we have more variables
            result = self.rewrite_sub_vars(result, depth=(depth + 1))

        return result

    @staticmethod
    def rewrite_sub_vars_with_values(expression, values):
        """Rewrite sub vars with actual variable values"""
        result = expression

        # replace each key we have a value for
        for key in values:
            rep_text = "##" + key + "##"
            rep_with = "" + str(values[key]) + ""

            result = result.replace(rep_text, rep_with)

        return result

    @staticmethod
    def values_to_dict(values):
        """Rewrite sub vars with actual variable values"""
        # Create dictionary of values
        values_dict_string = values.replace("(", "{")
        values_dict_string = values_dict_string.replace(")", "}")
        values_dict_string = values_dict_string.replace("'", '"')

        # for values or keys not quoted
        # Split by :
        values_split_string = values_dict_string
        # Trim stuff so we can get the key values
        values_split_string = values_split_string.replace(" ", "")
        values_split_string = values_split_string.replace("{", "")
        values_split_string = values_split_string.replace("}", "")

        values_split = values_split_string.split(",")
        values_split_final = []
        for value in values_split:
            values = value.split(":")
            values_split_final.extend(values)

        for value in values_split_final:
            if value[0] != "'" and value[-1] != "'":
                if value[0] != '"' and value[-1] != '"':
                    values_dict_string = values_dict_string.replace(
                        value, '"' + value + '"'
                    )

        values_dict = json.loads(values_dict_string)

        return values_dict

    def evaluate_fn_sub(self, expression):
        """ Return expression with values replaced """
        results = []

        # Builtins - Fudge some defaults here since we don't have runtime info
        # ${AWS::Region} ${AWS::AccountId}
        expression = self.rewrite_sub_vars_with_values(expression, self.SUBSTITUTION)

        # Handle Sub of form [ StringToSub, { "key" : "value", "key": "value" }]
        if "[" in expression:
            temp_expression = expression.split("[")[1].split(",")[0]
            values = expression.split("[")[1].split("(")[1].split(")")[0]
            values = self.values_to_dict("(" + values + ")")
            temp_expression = self.rewrite_sub_vars_with_values(temp_expression, values)
        else:
            temp_expression = expression.split("': '")[1].split("'")[0]

        # if we still have them we just use their values (ie: Parameters)
        result = self.rewrite_sub_vars(temp_expression)

        results.append(result)

        return results

    @staticmethod
    def evaluate_fn_join(expression):
        """ Return the joined stuff """
        results = []
        new_values_list = []

        temp = expression.split("[")[1]
        delimiter = temp.split(",")[0].strip("'")

        values = expression.split("[")[2]
        values = values.split("]]")[0]

        values_list = values.split(", ")
        for value in values_list:
            new_values_list.append(value.strip("'"))

        result = delimiter.join(new_values_list)
        results.append(result)

        return results

    @staticmethod
    def evaluate_fn_if(expression):
        """ Return both possible parts of the expression """
        results = []
        value_true = expression.split(",")[1].strip()
        value_false = expression.split(",")[2].strip().strip("]")
        # if we don't have '' this can break things
        results.append("'" + value_true.strip("'") + "'")
        results.append("'" + value_false.strip("'") + "'")
        return results

    def evaluate_fn_ref(self, expression):
        """Since this is runtime data the best we can do is the name in place"""
        # TODO: Allow user to inject RunTime values for these
        results = []

        temp = expression.split(": ")[1]
        if temp.strip("'") in self.SUBSTITUTION.keys():
            temp = self.SUBSTITUTION[temp.strip("'")]
            temp = "'" + temp + "'"

        results.append(temp)

        return results

    def find_in_map_lookup(self, mappings_map, first_key, final_key):
        step1 = self.mappings[mappings_map.strip("'")]
        step2 = step1[first_key.strip("'")]
        result = step2[final_key.strip("'")]
        return result

    def evaluate_fn_findinmap(self, expression):
        result = []

        mappings_map = expression.split("[")[1].split("]")[0].split(",")[0].strip()
        first_key = expression.split("[")[1].split("]")[0].split(",")[1].strip()
        final_key = expression.split("[")[1].split("]")[0].split(",")[2].strip()

        result.append(
            "'" + self.find_in_map_lookup(mappings_map, first_key, final_key) + "'"
        )

        return result

    @staticmethod
    def evaluate_fn_getatt(expression):
        raise Exception("Fn::GetAtt: not supported")

    @staticmethod
    def evaluate_fn_split(expression):
        raise Exception("Fn::Split: not supported")

    def evaluate_expression_controller(self, expression):
        """Figure out what type of expression and pass off to handler"""
        results = []

        if "Fn::If" in expression:
            results = self.evaluate_fn_if(expression)

        elif "Fn::Sub" in expression:
            results = self.evaluate_fn_sub(expression)

        elif "Fn::Join" in expression:
            results = self.evaluate_fn_join(expression)

        elif "Ref" in expression:
            results = self.evaluate_fn_ref(expression)

        elif "Fn::FindInMap" in expression:
            results = self.evaluate_fn_findinmap(expression)

        elif "Fn::GetAtt" in expression:
            results = self.evaluate_fn_getatt(expression)

        elif "Fn::Split" in expression:
            results = self.evaluate_fn_split(expression)

        else:
            # This is a NON expression repl { and } with ( and ) to break recursion
            results.append("(" + expression + ")")

        return results

    def evaluate_string(self, template_url, depth=0):
        """Recursively find expressions in the URL and send them to be evaluated"""
        # Recursion bail out
        if depth > self.MAX_DEPTH:
            raise Exception(
                "Template URL contains more than {} levels or nesting".format(
                    self.MAX_DEPTH
                )
            )

        template_urls = []
        # Evaluate expressions
        if "{" in template_url:
            parts = template_url.split("{")
            parts = parts[-1].split("}")  # Last open bracket

            # This function will handle Fn::Sub Fn::If etc.
            replacements = self.evaluate_expression_controller(
                parts[0]
            )  # First closed bracket after

            for replacement in replacements:
                template_url_temp = template_url
                template_url_temp = template_url_temp.replace(
                    "{" + parts[0] + "}", replacement
                )

                evaluated_strings = self.evaluate_string(
                    template_url_temp, depth=(depth + 1)
                )
                for evaluated_string in evaluated_strings:
                    template_urls.append(evaluated_string)
        else:
            template_urls.append(template_url)

        return template_urls

    def _flatten_template_controller(self, template_url):
        """ Recursively evaluate subs/ifs"""
        url_list = []

        # Replace ${SOMEVAR} with ##SOMEVAR## so finding actual "expressions" is easier
        template_url_string = str(template_url)

        parts = template_url_string.split("${")
        if len(parts) > 1:
            template_url_string = self.rewrite_vars(template_url_string)

        # Evaluate expressions recursively
        if "{" in template_url_string:
            replacements = self.evaluate_string(
                template_url_string
            )  # first closed bracket
            for replacement in replacements:
                url_list.append(replacement)

        else:
            url_list.append(template_url)

        return url_list

    def flatten_template_url(self, template_url):
        """Flatten template_url and return all permutations"""
        path_list = []

        url_list = self._flatten_template_controller(template_url)

        # Extract the path portion from the URL
        for url in url_list:
            # TODO: figure where the ' is coming from
            output = urlparse(str(url.strip("'")))
            path_list.append(output.path)

        path_list = list(dict.fromkeys(path_list))
        # print(url_list)
        # print(path_list)
        return path_list

    @staticmethod
    def _remove_one_level(path_string):
        result = path_string

        result = result.find("/", 0)
        result = path_string[result + 1 : len(path_string)]

        return result

    def find_local_child_template(self, parent_template_path, child_template_path):
        final_template_path = ""

        # Start where the Parent template is
        project_root = Path(os.path.dirname(parent_template_path))

        # Get rid of any "//"
        child_template_path_tmp = os.path.normpath(child_template_path)

        # Take the path piece by piece and try in current folder
        while "/" in str(child_template_path_tmp):
            child_template_path_tmp = self._remove_one_level(child_template_path_tmp)
            final_template_path = Path(
                "/".join([str(project_root), str(child_template_path_tmp)])
            )
            if final_template_path.exists() and final_template_path.is_file():
                return str(final_template_path)

        # Take the path piece by piece and try in one folder up folder
        project_root = Path(
            os.path.normpath(os.path.dirname(parent_template_path) + "/../")
        )
        # Get rid of any "//"
        child_template_path_tmp = os.path.normpath(child_template_path)

        while "/" in str(child_template_path_tmp):
            child_template_path_tmp = self._remove_one_level(child_template_path_tmp)
            final_template_path = Path(
                "/".join([str(project_root), str(child_template_path_tmp)])
            )
            if final_template_path.exists() and final_template_path.is_file():
                return str(final_template_path)

        return ""

    def template_url_to_path(
        self, current_template_path, template_url,
    ):
        child_local_paths = []
        child_template_paths = self.flatten_template_url(template_url)

        # TODO: Add logic to try for S3 paths
        for child_template_path in child_template_paths:
            child_local_paths.append(
                self.find_local_child_template(
                    current_template_path, child_template_path
                )
            )

        return child_local_paths
