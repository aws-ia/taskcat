from __future__ import print_function

import os
import unittest
from pathlib import Path

import yaml
import mock

from taskcat._cfn_lint import Lint
from taskcat._config import Config

class MockClientConfig(object):
    def __init__(self):
        self.region_name = "us-east-2"



test_two_path = str(
    Path(
        "/tmp/lint_test/test-config-two/templates/taskcat_test_" "template_test1"
    ).resolve()
)
test_cases = [
    {
        "config": {
            "global": {"qsname": "test-config", "regions": ["eu-west-1"]},
            "tests": {"test1": {}},
        },
        "templates": {"test1": """{"Resources": {}}"""},
        "expected_lints": {
            "test1": {
                "regions": ["eu-west-1"],
                "template_file": Path(
                    "/tmp/lint_test/test-config/templates/taskcat_test_template_test1"
                ).resolve(),
                "results": {
                    str(
                        Path(
                            "/tmp/lint_test/test-config/templates/taskcat_test_template"
                            "_test1"
                        ).resolve()
                    ): []
                },
            }
        },
    },
    {
        "config": {
            "global": {"qsname": "test-config-two", "regions": ["eu-west-1"]},
            "tests": {"test1": {}},
        },
        "templates": {
            "test1": """{"Resources": {"Name": {"Type":"AWS::Not::Exist"}}}"""
        },
        "expected_lints": {
            "test1": {
                "regions": ["eu-west-1"],
                "results": {
                    str(
                        Path(
                            "/tmp/lint_test/test-config-two/templates/taskcat_test_"
                            "template_test1"
                        ).resolve()
                    ): [
                        f"[E3001: Basic CloudFormation Resource Check] (Invalid or "
                        f"unsupported Type AWS::Not::Exist for resource Name in "
                        f"eu-west-1) matched "
                        f"{test_two_path}:1"
                    ]
                },
                "template_file": Path(
                    "/tmp/lint_test/test-config-two/templates/taskcat_test_template"
                    "_test1"
                ).resolve(),
            }
        },
    },
    {
        "config": {
            "global": {"qsname": "test-config-three", "regions": ["eu-west-1"]},
            "tests": {"test1": {}},
        },
        "templates": {
            "test1": '{"Resources": {"Name": {"Type":"AWS::CloudFormation::Stack",'
            '"Properties":{"TemplateURL": "broken"}}}}'
        },
        "expected_lints": {
            "test1": {
                "regions": ["eu-west-1"],
                "template_file": Path(
                    "/tmp/lint_test/test-config-three/templates"
                    "/taskcat_test_template_test1"
                ).resolve(),
                "results": {
                    str(
                        Path(
                            "/tmp/lint_test/test-config-three/templates"
                            "/taskcat_test_template_test1"
                        ).resolve()
                    ): []
                },
            }
        },
    },
]


def mkdir(path, ignore_exists=True):
    os.makedirs(path, exist_ok=ignore_exists)


def flatten_rule(lints):
    for test in lints.keys():
        for result in lints[test]["results"].keys():
            for i in range(0, len(lints[test]["results"][result])):
                lints[test]["results"][result][i] = str(
                    lints[test]["results"][result][i]
                )
    return lints


class TestCfnLint(unittest.TestCase):
    @mock.patch(
        "taskcat._client_factory.ClientFactory._create_client",
        mock.MagicMock(return_value=MockClient()),
    )
    def test_lint(self):
        base_path = "/tmp/lint_test/"
        mkdir(base_path)
        try:
            for test_case in test_cases:
                qs_path = base_path + test_case["config"]["global"]["qsname"] + "/"
                print(qs_path)
                mkdir(qs_path)
                mkdir(qs_path + "ci")
                mkdir(qs_path + "templates")
                os.chdir(qs_path)
                template_path = "taskcat_test_template"
                config_path = "./ci/taskcat_test_config"
                for test in test_case["config"]["tests"].keys():
                    template_file = template_path + "_" + test
                    test_case["config"]["tests"][test]["template_file"] = template_file
                    with open("./templates/" + template_file, "w") as f:
                        f.write(test_case["templates"][test])
                with open(config_path, "w") as f:
                    f.write(yaml.safe_dump(test_case["config"]))
                config = Config(
                    project_config_path=str(config_path), project_root="../"
                )
                lint = Lint(config=config)
                self.assertEqual(
                    test_case["expected_lints"], flatten_rule(lint.lints[0])
                )
        finally:
            # shutil.rmtree(base_path)
            pass
