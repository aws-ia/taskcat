from __future__ import print_function

import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from io import StringIO

import yaml

from taskcat.cfn_lint import Lint

test_cases = [
    {
        "config": {
            "global": {
                "qsname": "test-config",
                "regions": ["eu-west-1"]
            },
            "tests": {
                "test1": {}
            }
        },
        "templates": {
            "test1": """{"Resources": {}}"""
        },
        "expected_lints": {'test1': {'regions': ['eu-west-1'], 'template_file': 'templates/taskcat_test_template_test1',
                                     'results': {'templates/taskcat_test_template_test1': []}}},
        "expected_output": "\x1b[0;30;43m[INFO   ]\x1b[0m :Lint passed for test test1 on template templates/taskcat_test_template_test1:\n"
    },
    {
        "config": {
            "global": {
                "qsname": "test-config2",
                "regions": ["eu-west-1"]
            },
            "tests": {
                "test1": {}
            }
        },
        "templates": {
            "test1": """{"Resources": {"Name": {"Type":"AWS::Not::Exist"}}}"""
        },
        "expected_lints": {'test1': {'regions': ['eu-west-1'],
           'results': {'templates/taskcat_test_template_test1': [
               '[E3001: Basic CloudFormation Resource Check] (Invalid or unsupported Type AWS::Not::Exist for resource Name in eu-west-1) matched templates/taskcat_test_template_test1:1']},
           'template_file': 'templates/taskcat_test_template_test1'}},
        "expected_output": """[0;30;41m[ERROR  ][0m :Lint detected issues for test test1 on template templates/taskcat_test_template_test1:
[0;30;41m[ERROR  ][0m :    line 1 [E3001] [Basic CloudFormation Resource Check] (Invalid or unsupported Type AWS::Not::Exist for resource Name in eu-
                      west-1)
"""
    },
    {
        "config": {
            "global": {
                "qsname": "test-config3",
                "regions": ["eu-west-1"]
            },
            "tests": {
                "test1": {}
            }
        },
        "templates": {
            "test1": """{
    "Parameters": {
        "BadJson": {
            "AllowedPattern": "\/"
        }
    }
}"""
        },
        "expected_lints": {'test1': {'regions': ['eu-west-1'], 'template_file': 'templates/taskcat_test_template_test1',
                                     'results': {}}},
        "expected_output": "",
        "expected_error_output": '[0;30;41m[ERROR  ][0m :Linter failed to load template templates/taskcat_test_template_test1 "found unknown escape character" line 3, column 31\n'
    },
    {
        "config": {
            "global": {
                "qsname": "test-config4",
                "regions": ["eu-west-1"]
            },
            "tests": {
                "test1": {}
            }
        },
        "templates": {
            "test1": """{"Resources": {"Name": {"Type":"AWS::CloudFormation::Stack","Properties":{"TemplateURL": "broken"}}}}"""
        },
        "expected_lints": {'test1': {'regions': ['eu-west-1'], 'template_file': 'templates/taskcat_test_template_test1',
                                     'results': {'templates/taskcat_test_template_test1': []}}},
        "expected_output": "[0;30;43m[INFO   ][0m :Lint passed for test test1 on template templates/taskcat_test_template_test1:\n",
        "expected_error_output": """[0;30;41m[ERROR  ][0m :Linter failed to load template broken "[Errno 2] No such file or directory: 'broken'"\n"""
    }
]


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def mkdir(path, ignore_exists=True):
    os.makedirs(path, exist_ok=ignore_exists)


def flatten_rule(lints):
    for test in lints.keys():
        for result in lints[test]["results"].keys():
            for i in range(0, len(lints[test]["results"][result])):
                lints[test]["results"][result][i] = str(lints[test]["results"][result][i])
    return lints


class TestCfnLint(unittest.TestCase):

    def test_lint(self):
        base_path = "/tmp/lint_test/"
        mkdir(base_path)
        try:
            for test_case in test_cases:
                qs_path = base_path + test_case["config"]["global"]["qsname"] + "/"
                mkdir(qs_path)
                mkdir(qs_path + 'ci')
                mkdir(qs_path + 'templates')
                os.chdir(qs_path)
                template_path = "taskcat_test_template"
                config_path = "./ci/taskcat_test_config"
                for test in test_case['config']["tests"].keys():
                    template_file = template_path + "_" + test
                    test_case['config']["tests"][test]["template_file"] = template_file
                    with open("./templates/" + template_file, 'w') as f:
                        f.write(test_case["templates"][test])
                with open(config_path, 'w') as f:
                    f.write(yaml.safe_dump(test_case['config']))
                with captured_output() as (out, err):
                    lint = Lint(config=config_path)
                if 'expected_error_output' in test_case.keys():
                    self.assertEqual(test_case['expected_error_output'], out.getvalue())
                lint.lints = flatten_rule(lint.lints)
                self.assertEqual(test_case['expected_lints'], lint.lints)
                with captured_output() as (out, err):
                    lint.output_results()
                self.assertEqual(test_case['expected_output'], out.getvalue())
        finally:
            shutil.rmtree(base_path)

