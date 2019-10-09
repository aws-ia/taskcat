import unittest
from pathlib import Path

import mock
from taskcat import Config


@mock.patch("taskcat._client_factory.Boto3Cache", autospec=True)
def get_mock_boto_cache(m_boto):
    return m_boto()


class TestCfnTemplate(unittest.TestCase):
    @mock.patch("taskcat._cfn.template.s3_url_maker", return_value="test-url")
    def test_upload(self, m_s3_url_maker):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        boto_cache = get_mock_boto_cache()
        templates = c.get_templates(boto3_cache=boto_cache, project_root=test_proj)
        template = templates["taskcat-json"]
        resp = template._upload("my-bucket", "my-prefix")
        self.assertEqual(resp, "test-url")
        template.boto3_cache.client.assert_called_once()
        m_s3_url_maker.assert_called_once()

    def test_delete_s3_object(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        boto_cache = get_mock_boto_cache()
        templates = c.get_templates(boto3_cache=boto_cache, project_root=test_proj)
        template = templates["taskcat-json"]
        template._delete_s3_object("s3://bucket_name/prefix/file")
        template.s3_client.delete_objects.assert_called_once()

    @mock.patch("taskcat._cfn.template.Template._upload", return_value="test-resp")
    def test_create_temp_s3_object(self, m_upload):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        boto_cache = get_mock_boto_cache()
        templates = c.get_templates(boto3_cache=boto_cache, project_root=test_proj)
        template = templates["taskcat-json"]
        resp = template._create_temporary_s3_object("test_bucket", "test_prefix")
        self.assertEqual(resp, "test-resp")
        template.url = "a-url"
        resp = template._create_temporary_s3_object("test_bucket", "test_prefix")
        self.assertEqual(resp, "")

    def test_do_validate(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        boto_cache = get_mock_boto_cache()
        templates = c.get_templates(boto3_cache=boto_cache, project_root=test_proj)
        template = templates["taskcat-json"]
        template._do_validate("some-url", "some-region")
        calls = [c[0] for c in template.boto3_cache.mock_calls]
        self.assertIn("session().client().validate_template", calls)

    @mock.patch("taskcat._cfn.template.Template._create_temporary_s3_object")
    @mock.patch(
        "taskcat._cfn.template.Template._do_validate", return_value=(None, None)
    )
    @mock.patch("taskcat._cfn.template.Template._delete_s3_object")
    def test_validate(self, m_delete, m_do_val, m_create):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        boto_cache = get_mock_boto_cache()
        templates = c.get_templates(boto3_cache=boto_cache, project_root=test_proj)
        template = templates["taskcat-json"]
        with self.assertRaises(ValueError) as _:
            resp = template.validate("us-east-1")
        resp = template.validate("us-east-1", "my-bucket")
        self.assertEqual(None, resp)
        m_delete.assert_called_once()
        m_do_val.assert_called_once()
        m_create.assert_called_once()
