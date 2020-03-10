import json
import unittest

import cfnlint
from taskcat._cfn.stack_url_helper import StackURLHelper


class TestStackURLHelper(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @staticmethod
    def _load_template(template_path):
        try:
            cfn = cfnlint.decode.cfn_yaml.load(template_path)
        except Exception:
            # print("Exception parsing: '{}'".format(template_path))
            exit(1)
        return cfn

    # Test TemplateURL to path extraction
    def test_flatten_template_url(self):
        with open("tests/data/stackurlhelper/test.json") as test_file:
            self.testers = json.load(test_file)
            self.testers = self.testers["tests"]

        total = len(self.testers)
        matched = 0

        for test in self.testers:
            helper = StackURLHelper()
            cfn = self._load_template(test["input"]["master_template"])
            helper.mappings = cfn.get("Mappings")
            helper.template_parameters = cfn.get("Parameters")

            # Setup default parameters
            default_parameters = {}
            for parameter in helper.template_parameters:
                properties = helper.template_parameters.get(parameter)
                if "Default" in properties.keys():
                    default_parameters[parameter] = properties["Default"]

            helper.SUBSTITUTION.update(default_parameters)

            test["input"]["parameter_values"] = {}

            # Inject Parameter Values
            if "parameter_values" in test["input"]:
                parameter_values = test["input"]["parameter_values"]
                helper.SUBSTITUTION.update(parameter_values)

            # print(test)
            # print(test["output"]["url_paths"])
            # print(helper.flatten_template_url(test["input"]["child_template"]))
            if test["output"]["url_paths"] == helper.flatten_template_url(
                test["input"]["child_template"],
            ):

                matched = matched + 1
        # print("matched {} total {}".format(matched, total))
        self.assertEqual(matched, total)

    def test_flatten_template_url_exceptions_split(self):
        helper = StackURLHelper()
        with self.assertRaises(Exception) as context:
            helper.flatten_template_url("{'Fn::Split'}")

        self.assertTrue("Fn::Split: not supported" in str(context.exception))

    def test_flatten_template_url_exceptions_getatt(self):
        helper = StackURLHelper()
        with self.assertRaises(Exception) as context:
            helper.flatten_template_url("{'Fn::GetAtt'}")

        self.assertTrue("Fn::GetAtt: not supported" in str(context.exception))

    def test_flatten_template_url_maxdepth(self):
        helper = StackURLHelper()
        with self.assertRaises(Exception) as context:
            helper.flatten_template_url(
                "{1{2{3{4{5{6{7{8{9{{{{{{{{{{{{21}}}}}}}}}}}}}}}}}}}}}"
            )

        self.assertTrue("Template URL contains more than" in str(context.exception))

    # Test TemplateURL to path extraction
    def test_find_local_child_template(self):
        with open("tests/data/stackurlhelper/test.json") as test_file:
            self.tests = json.load(test_file)
            self.tests = self.tests["tests"]

        total = 0
        matched = 0
        helper = StackURLHelper()
        for test in self.tests:
            index = 0
            for url_path in test["output"]["url_paths"]:
                total = total + 1
                master_template = test["input"]["master_template"]
                result = helper.find_local_child_template(master_template, url_path)
                expected = test["output"]["local_paths"][index]
                if str(result) == str(expected):
                    matched = matched + 1
                index = index + 1

        # print("matched {} total {}".format(matched, total))
        self.assertEqual(matched, total)

    def test_fn_findinmap_lookup(self):
        l_mappings = {
            "ami_lookup": {
                "us-east-1": {"ami": "this_one", "ami2": "that_one"},
                "us-east-2": {"ami": "is_this_one", "ami2": "is_that_one"},
                "us-west-1": {"ami": "not_this_one", "ami2": "not_that_one"},
            }
        }

        helper = StackURLHelper()
        helper.mappings = l_mappings

        mappings_map = "ami_lookup"
        first_key = "us-west-1"
        final_key = "ami2"

        result = helper.find_in_map_lookup(mappings_map, first_key, final_key)

        self.assertEqual(result, "not_that_one")

    # TODO: Test all the individual functions
    # TODO: Test fn_sub logic
    # def test_fn_sub(self):
    #     self.assertEqual(True, False)

    # TODO: Test local path Discovery
    # def test_fn_if(self):
    #     self.assertEqual(True, False)
