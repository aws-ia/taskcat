import os
import shutil
import unittest
from pathlib import Path

import mock
import yaml

from taskcat._cfn_lint import Lint
from taskcat._config import Config
from taskcat._config_types import AWSRegionObject


class MockClientConfig(object):
    def __init__(self):
        self.region_name = "us-east-2"


class MockClient(object):
    def __init__(self):
        self._client_config = MockClientConfig()


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


def build_test_case(base_path, test_case):
    qs_path = base_path + test_case["config"]["global"]["qsname"] + "/"
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
    return config_path


class TestCfnLint(unittest.TestCase):
    @mock.patch(
        "taskcat._client_factory.ClientFactory.create_client",
        mock.MagicMock(return_value=MockClient()),
    )
    def test_lint(self):
        cwd = os.getcwd()
        base_path = "/tmp/lint_test/"
        mkdir(base_path)
        try:
            for test_case in test_cases:
                config = Config(
                    project_config_path=str(build_test_case(base_path, test_case)),
                    project_root="../",
                    create_clients=False,
                )
                lint = Lint(config=config)
                self.assertEqual(
                    test_case["expected_lints"], flatten_rule(lint.lints[0])
                )
        finally:
            shutil.rmtree(base_path)
            os.chdir(cwd)
            pass

    def test_filter_unsupported_regions(self):
        mock_cf = mock.MagicMock()
        regions = [
            AWSRegionObject(region_name="us-east-1", client_factory=mock_cf),
            AWSRegionObject(region_name="us-east-2", client_factory=mock_cf),
            AWSRegionObject(region_name="eu-central-1", client_factory=mock_cf),
        ]
        supported = Lint._filter_unsupported_regions(regions)
        expected = [r.name for r in regions]
        self.assertCountEqual(supported, expected)
        supported = Lint._filter_unsupported_regions(
            regions
            + [AWSRegionObject(region_name="non-exist-1", client_factory=mock_cf)]
        )
        self.assertCountEqual(supported, expected)

    @mock.patch("taskcat._cfn_lint.LOG.info")
    @mock.patch("taskcat._cfn_lint.LOG.warning")
    @mock.patch("taskcat._cfn_lint.LOG.error")
    def test_output_results(self, mock_log_error, mock_log_warning, mock_log_info):
        cwd = os.getcwd()
        try:
            lint = Lint(
                config=Config(
                    project_config_path=str(
                        build_test_case("/tmp/lint_test_output/", test_cases[0])
                    ),
                    project_root="../",
                    create_clients=False,
                )
            )
            lint.output_results()
            self.assertTrue(
                mock_log_info.call_args[0][0].startswith(
                    "Lint passed for test test1 on template "
                )
            )
            self.assertEqual(mock_log_error.called, False)
            self.assertEqual(mock_log_warning.called, False)

            mock_log_info.reset_mock()
            lint_key = [t for t in lint.lints[0]][0]
            result_key = [t for t in lint.lints[0][lint_key]["results"]][0]
            test = lint.lints[0][lint_key]["results"][result_key]
            rule = mock.Mock(return_val="[W0001] some warning")
            rule.rule.id = "W0001"
            rule.linenumber = 123
            rule.rule.shortdesc = "short warning"
            rule.message = "some warning"
            test.append(rule)
            lint.output_results()
            self.assertTrue(
                mock_log_warning.call_args_list[0][0][0].startswith(
                    "Lint detected issues for test test1 on template "
                )
            )
            mock_log_warning.assert_has_calls(
                [mock.call("    line 123 [0001] [short warning] some warning")]
            )
            self.assertEqual(mock_log_info.called, False)
            self.assertEqual(mock_log_error.called, False)

            mock_log_warning.reset_mock()
            test.pop(0)
            rule = mock.Mock(return_val="[E0001] some error")
            rule.rule.id = "E0001"
            rule.linenumber = 123
            rule.rule.shortdesc = "short error"
            rule.message = "some error"
            test.append(rule)
            lint.output_results()
            self.assertTrue(
                mock_log_warning.call_args[0][0].startswith(
                    "Lint detected issues for test test1 on template "
                )
            )
            mock_log_error.assert_called_once_with(
                "    line 123 [0001] [short error] some error"
            )
            self.assertEqual(mock_log_info.called, False)
        finally:
            shutil.rmtree("/tmp/lint_test_output/")
            os.chdir(cwd)
            pass

    def test_passed(self):
        cwd = os.getcwd()
        try:
            lint = Lint(
                config=Config(
                    project_config_path=str(
                        build_test_case("/tmp/lint_test_output/", test_cases[0])
                    ),
                    project_root="../",
                    create_clients=False,
                )
            )
            self.assertEqual(lint.passed, True)

            lint_key = [t for t in lint.lints[0]][0]
            result_key = [t for t in lint.lints[0][lint_key]["results"]][0]
            test = lint.lints[0][lint_key]["results"][result_key]
            rule = mock.Mock(return_val="[E0001] some error")
            rule.rule.id = "E0001"
            rule.linenumber = 123
            rule.rule.shortdesc = "short error"
            rule.message = "some error"
            test.append(rule)
            lint.strict = True
            self.assertEqual(lint.passed, False)
        finally:
            shutil.rmtree("/tmp/lint_test_output/")
            os.chdir(cwd)
            pass
