import os
import unittest
from pathlib import Path
from unittest import mock

from taskcat._client_factory import Boto3Cache
from taskcat._config import Config
from taskcat.exceptions import TaskCatException


class TestNewConfig(unittest.TestCase):
    def test_config(self):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/config_inheritance").resolve()

        config = Config.create(
            args={"project": {"build_submodules": False}},
            global_config_path=base_path / ".taskcat_global.yml",
            project_config_path=base_path / "./.taskcat.yml",
            overrides_path=base_path / "./.taskcat_overrides.yml",
            env_vars={"TASKCAT_PROJECT_PACKAGE_LAMBDA": "False"},
        )

        expected = {
            "general": {
                "parameters": {
                    "GlobalVar": "set_in_global",
                    "OverridenVar": "set_in_global",
                },
                "s3_bucket": "set-in-global",
                "s3_regional_buckets": False,
            },
            "project": {
                "regions": ["us-east-1"],
                "package_lambda": False,
                "lambda_zip_path": "lambda_functions/packages",
                "lambda_source_path": "lambda_functions/source",
                "parameters": {
                    "GlobalVar": "set_in_global",
                    "OverridenVar": "set_in_global",
                    "ProjectVar": "set_in_project",
                },
                "build_submodules": False,
                "template": "template1.yaml",
                "s3_bucket": "set-in-global",
                "s3_enable_sig_v2": False,
                "shorten_stack_name": False,
                "s3_regional_buckets": False,
            },
            "tests": {
                "default": {
                    "parameters": {
                        "MyVar": "set_in_test",
                        "OverridenVar": "set_in_global",
                        "ProjectVar": "set_in_project",
                        "GlobalVar": "set_in_global",
                    },
                    "regions": ["us-west-2"],
                    "s3_bucket": "set-in-global",
                    "template": "template1.yaml",
                    "s3_regional_buckets": False,
                },
                "other": {
                    "template": "other_template.yaml",
                    "parameters": {
                        "ProjectVar": "set_in_project",
                        "OverridenVar": "set_in_global",
                        "GlobalVar": "set_in_global",
                    },
                    "regions": ["us-east-1"],
                    "s3_bucket": "set-in-global",
                    "s3_regional_buckets": False,
                },
            },
        }

        expected_source = {
            "general": {
                "s3_bucket": str(base_path / ".taskcat_global.yml"),
                "parameters": {
                    "GlobalVar": str(base_path / ".taskcat_global.yml"),
                    "OverridenVar": str(base_path / ".taskcat_global.yml"),
                },
                "s3_regional_buckets": str(base_path / ".taskcat_global.yml"),
            },
            "project": {
                "s3_bucket": str(base_path / ".taskcat_global.yml"),
                "s3_enable_sig_v2": "TASKCAT_DEFAULT",
                "s3_regional_buckets": str(base_path / ".taskcat_global.yml"),
                "shorten_stack_name": "TASKCAT_DEFAULT",
                "package_lambda": "EnvoronmentVariable",
                "lambda_zip_path": "TASKCAT_DEFAULT",
                "lambda_source_path": "TASKCAT_DEFAULT",
                "build_submodules": "CliArgument",
                "parameters": {
                    "GlobalVar": str(base_path / ".taskcat_global.yml"),
                    "OverridenVar": str(base_path / ".taskcat_global.yml"),
                    "ProjectVar": str(base_path / ".taskcat.yml"),
                },
                "regions": str(base_path / ".taskcat.yml"),
                "template": str(base_path / ".taskcat.yml"),
            },
            "tests": {
                "default": {
                    "s3_bucket": str(base_path / ".taskcat_global.yml"),
                    "s3_regional_buckets": str(base_path / ".taskcat_global.yml"),
                    "template": str(base_path / ".taskcat.yml"),
                    "parameters": {
                        "GlobalVar": str(base_path / ".taskcat_global.yml"),
                        "MyVar": str(base_path / ".taskcat.yml"),
                        "OverridenVar": str(base_path / ".taskcat_global.yml"),
                        "ProjectVar": str(base_path / ".taskcat.yml"),
                    },
                    "regions": str(base_path / ".taskcat.yml"),
                },
                "other": {
                    "s3_bucket": str(base_path / ".taskcat_global.yml"),
                    "s3_regional_buckets": str(base_path / ".taskcat_global.yml"),
                    "template": str(base_path / ".taskcat.yml"),
                    "parameters": {
                        "GlobalVar": str(base_path / ".taskcat_global.yml"),
                        "ProjectVar": str(base_path / ".taskcat.yml"),
                        "OverridenVar": str(base_path / ".taskcat_global.yml"),
                    },
                    "regions": str(base_path / ".taskcat.yml"),
                },
            },
        }

        self.assertEqual(expected, config.config.to_dict())
        self.assertEqual(expected_source, config.config._source)

    def test_legacy_config(self):

        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/legacy_test").resolve()

        new_config_location = base_path / ".taskcat.yml"
        new_overrides_location = base_path / ".taskcat_overrides.yml"

        if new_config_location.is_file():
            new_config_location.unlink()
        if new_overrides_location.is_file():
            new_overrides_location.unlink()

        Config.create(
            project_root=base_path,
            project_config_path=new_config_location,
            overrides_path=new_overrides_location,
        )

        self.assertTrue(new_config_location.is_file())
        self.assertTrue(new_overrides_location.is_file())

        # should not raise even if both legacy and current format files are present
        Config.create(
            project_root=base_path,
            project_config_path=new_config_location,
            overrides_path=new_overrides_location,
        )

    def test_standalone_template(self):

        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/legacy_test/templates/").resolve()

        Config.create(template_file=base_path / "test.template.yaml")

    def test_no_parameters(self):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/create_no_params/").resolve()

        Config.create(
            project_root=base_path, project_config_path=base_path / ".taskcat.yml"
        )

    @mock.patch("taskcat._config.Boto3Cache.account_id", return_value="123412341234")
    @mock.patch("taskcat._config.Boto3Cache.partition", return_value="aws")
    def test_get_regions(self, _, __):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/regional_client_and_bucket").resolve()

        config = Config.create(
            args={},
            global_config_path=base_path / ".taskcat_global.yml",
            project_config_path=base_path / "./.taskcat.yml",
            overrides_path=base_path / "./.taskcat_overrides.yml",
            env_vars={},
        )
        sessions = config.get_regions()
        for test_name, regions in sessions.items():
            with self.subTest(test=test_name):
                for region_name, region_obj in regions.items():
                    with self.subTest(region=region_name):
                        self.assertEqual(region_name, region_obj.name)
                        if test_name == "json-test" and region_name == "eu-central-1":
                            self.assertEqual("special-use-case", region_obj.profile)
                        elif test_name == "yaml-test" and region_name == "sa-east-1":
                            self.assertEqual("default", region_obj.profile)
                        elif region_name == "me-south-1":
                            self.assertEqual("mes1", region_obj.profile)
                        elif region_name == "ap-east-1":
                            self.assertEqual("hongkong", region_obj.profile)
                        elif test_name == "yaml-test":
                            self.assertEqual("foobar", region_obj.profile)
                        else:
                            self.assertEqual("default", region_obj.profile)

    @mock.patch("taskcat._config.Boto3Cache.account_id", return_value="123412341234")
    @mock.patch("taskcat._config.Boto3Cache.partition", return_value="aws")
    @mock.patch("taskcat._config.S3BucketObj.create", return_value=None)
    @mock.patch("taskcat._client_factory.boto3", autospec=True)
    def test_get_buckets(self, _, __, ___, m_boto):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/regional_client_and_bucket").resolve()

        config = Config.create(
            args={},
            global_config_path=base_path / ".taskcat_global.yml",
            project_config_path=base_path / "./.taskcat.yml",
            overrides_path=base_path / "./.taskcat_overrides.yml",
            env_vars={},
        )
        mock_boto_cache = Boto3Cache(_boto3=m_boto)
        buckets = config.get_buckets(boto3_cache=mock_boto_cache)
        bucket_acct = {}
        for test_name, regions in buckets.items():
            with self.subTest(test=test_name):
                for region_name, region_obj in regions.items():
                    with self.subTest(region=region_name):
                        if not bucket_acct.get(region_obj.account_id):
                            bucket_acct[region_obj.account_id] = region_obj.name
                        self.assertEqual(
                            bucket_acct[region_obj.account_id], region_obj.name
                        )
                        region_obj.delete()

    @mock.patch("taskcat._config.Boto3Cache.account_id", return_value="123412341234")
    @mock.patch("taskcat._config.Boto3Cache.partition", return_value="aws")
    @mock.patch("taskcat._config.S3BucketObj.create", return_value=None)
    @mock.patch("taskcat._client_factory.boto3", autospec=True)
    def test_get_buckets_regional(self, _, __, ___, m_boto):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/regional_client_and_bucket").resolve()

        config = Config.create(
            args={},
            global_config_path=base_path / ".taskcat_global_regional_bucket.yml",
            project_config_path=base_path / "./.taskcat.yml",
            overrides_path=base_path / "./.taskcat_overrides.yml",
            env_vars={},
        )
        mock_boto_cache = Boto3Cache(_boto3=m_boto)
        buckets = config.get_buckets(boto3_cache=mock_boto_cache)
        for test_name, regions in buckets.items():
            with self.subTest(test=test_name):
                for region_name, bucket_obj in regions.items():
                    self.assertEqual(bucket_obj.account_id, "123412341234")
                    self.assertEqual(bucket_obj.region, region_name)
                    self.assertTrue(bucket_obj.auto_generated)
                    self.assertTrue(bucket_obj.sigv4, True)
                    self.assertEqual(bucket_obj.partition, "aws")
                    self.assertEqual(
                        bucket_obj.name,
                        f"tcat-13725204b43e5bf5a37800c23614ee21-{region_name}",
                    )

    @mock.patch("taskcat._config.Boto3Cache.account_id", return_value="123412341234")
    @mock.patch("taskcat._config.Boto3Cache.partition", return_value="aws")
    @mock.patch("taskcat._config.S3BucketObj.create", return_value=None)
    @mock.patch(
        "taskcat._config.ParamGen._get_license_content_wrapper",
        return_value="a-license-key",
    )
    @mock.patch("taskcat._config.Boto3Cache", autospec=True)
    def test_get_rendered_params(self, _, __, ___, ____, m_boto):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/regional_client_and_bucket").resolve()
        m_boto.client.return_value = mock_client()
        config = Config.create(
            args={},
            project_root=base_path,
            global_config_path=base_path / ".taskcat_global.yml",
            project_config_path=base_path / "./.taskcat.yml",
            overrides_path=base_path / "./.taskcat_overrides.yml",
            env_vars={},
        )
        regions = config.get_regions(boto3_cache=m_boto)
        buckets = config.get_buckets(boto3_cache=m_boto)
        templates = config.get_templates()
        rendered_params = config.get_rendered_parameters(buckets, regions, templates)
        for test_name, regions in rendered_params.items():
            with self.subTest(test=test_name):
                for region_name, _params in regions.items():
                    with self.subTest(region=region_name):
                        buckets[test_name][region_name].delete()

    def test_get_templates(self):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/regional_client_and_bucket").resolve()
        config = Config.create(
            args={},
            project_root=base_path,
            global_config_path=base_path / ".taskcat_global.yml",
            project_config_path=base_path / "./.taskcat.yml",
            overrides_path=base_path / "./.taskcat_overrides.yml",
            env_vars={},
        )
        templates = config.get_templates()
        for test_name, _template in templates.items():
            with self.subTest(test=test_name):
                pass

    @mock.patch("taskcat._config.LOG", autospec=True)
    def test__dict_from_template(self, mock_log):
        root_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(root_path + "data/regional_client_and_bucket").resolve()
        template = base_path / "templates/debug-yaml.template"
        # valid config
        template_dict = Config._dict_from_template(template)
        self.assertEqual(True, isinstance(template_dict, dict))

        # invalid path
        with self.assertRaises(TaskCatException):
            Config._dict_from_template(base_path / "invalid-path")

        # cannot create template object
        with mock.patch("taskcat._config.Template") as mock_template:
            exc = ValueError("fail")
            mock_template.side_effect = exc
            with self.assertRaises(ValueError) as e:
                Config._dict_from_template(template)
            self.assertEqual(exc, e.exception)
            mock_log.warning.assert_called_once()

        base_path = Path(root_path + "data/standalone_template").resolve()

        # metadata in taskcat, but no taskcat key
        template = base_path / "test.template_no_tc_meta.yaml"
        template_dict = Config._dict_from_template(template)
        self.assertEqual(True, isinstance(template_dict, dict))
        self.assertEqual(
            True, template_dict["project"]["template"].endswith("no_tc_meta.yaml")
        )
        self.assertEqual({}, template_dict["tests"]["default"]["parameters"])

        # empty dict taskcat metadata
        template = base_path / "test.template_tc_empty_meta.yaml"
        template_dict = Config._dict_from_template(template)
        self.assertEqual(True, isinstance(template_dict, dict))
        self.assertEqual(
            True, template_dict["project"]["template"].endswith("tc_empty_meta.yaml")
        )
        self.assertEqual({}, template_dict["tests"]["default"]["parameters"])

        # populated taskcat metadata
        template = base_path / "test.template_tc_full_meta.yaml"
        template_dict = Config._dict_from_template(template)
        self.assertEqual(True, isinstance(template_dict, dict))
        self.assertEqual(
            True, template_dict["project"]["template"].endswith("tc_full_meta.yaml")
        )
        self.assertEqual(
            {"SomeParam": "SomeValue"}, template_dict["tests"]["sometest"]["parameters"]
        )


def mock_client(*args, **kwargs):
    m = mock.Mock()
    m.describe_availability_zones = mock_get_azs
    return m


def mock_get_azs(*args, **kwargs):
    return {
        "AvailabilityZones": [
            {"ZoneName": "mo-ck-1a", "ZoneId": "mockzoneid1a"},
            {"ZoneName": "mo-ck-1b", "ZoneId": "mockzoneid1b"},
            {"ZoneName": "mo-ck-1c", "ZoneId": "mockzoneid1c"},
        ]
    }
