import errno
import os
import unittest
from unittest import mock

from taskcat._common_utils import (
    exit_with_code,
    fetch_ssm_parameter_value,
    get_s3_domain,
    make_dir,
    merge_dicts,
    name_from_stack_id,
    param_list_to_dict,
    pascal_to_snake,
    region_from_stack_id,
    s3_bucket_name_from_url,
    s3_key_from_url,
    s3_url_maker,
)
from taskcat.exceptions import TaskCatException


class TestCommonUtils(unittest.TestCase):
    def test_get_param_includes(self):
        bad_testcases = [{}, [[]], [{}]]
        for bad in bad_testcases:
            with self.assertRaises(TaskCatException):
                param_list_to_dict(bad)

    def test_region_from_stack_id(self):
        actual = region_from_stack_id("arn:::us-east-1")
        self.assertEqual("us-east-1", actual)

    def test_name_from_stack_id(self):
        actual = name_from_stack_id("arn:::us-east-1::Stack/test-name")
        self.assertEqual("test-name", actual)

    @mock.patch("taskcat._common_utils.get_s3_domain", return_value="amazonaws.com")
    def test_s3_url_maker(self, m_get_s3_domain):
        m_s3 = mock.Mock()
        m_s3.get_bucket_location.return_value = {"LocationConstraint": None}
        actual = s3_url_maker("test-bucket", "test-key/1", m_s3)

        self.assertEqual(
            "https://test-bucket.s3.us-east-1.amazonaws.com/test-key/1", actual
        )
        m_s3.get_bucket_location.return_value = {"LocationConstraint": "us-west-2"}

        actual = s3_url_maker("test-bucket", "test-key/1", m_s3)
        self.assertEqual(
            "https://test-bucket.s3.us-west-2.amazonaws.com/test-key/1", actual
        )
        m_get_s3_domain.assert_called_once()

    def test_get_s3_domain(self):
        actual = get_s3_domain("cn-north-1")
        self.assertEqual("amazonaws.com.cn", actual)
        with self.assertRaises(TaskCatException):
            get_s3_domain("totally-invalid-region")

    def test_merge_dicts(self):
        input = [{}, {}]
        actual = merge_dicts(input)
        self.assertEqual({}, actual)
        input = [{"a": 1}, {"b": 2}]
        actual = merge_dicts(input)
        self.assertEqual({"a": 1, "b": 2}, actual)

    def test_pascal_to_snake(self):
        actual = pascal_to_snake("MyParam")
        self.assertEqual("my_param", actual)
        actual = pascal_to_snake("VPCParam")
        self.assertEqual("vpcparam", actual)

    def test_make_dir(self):
        path = "/tmp/test_make_dir_path"
        try:
            os.rmdir(path)
        except FileNotFoundError:
            pass
        os.makedirs(path)
        make_dir(path)
        os.rmdir(path)
        make_dir(path)
        self.assertEqual(os.path.isdir(path), True)
        with self.assertRaises(FileExistsError) as cm:
            make_dir(path, False)
        self.assertEqual(cm.exception.errno, errno.EEXIST)
        os.rmdir(path)

    @mock.patch("taskcat._common_utils.sys.exit", autospec=True)
    @mock.patch("taskcat._common_utils.LOG", autospec=True)
    def test_exit_with_code(self, mock_log, mock_exit):
        exit_with_code(1)
        mock_log.error.assert_not_called()
        mock_exit.assert_called_once_with(1)
        mock_exit.reset_mock()
        exit_with_code(0, "msg")
        mock_exit.assert_called_once_with(0)
        mock_exit.assert_called_once()

    def test_s3_key_from_url(self):
        k = s3_key_from_url("https://testbuk.s3.amazonaws.com/testprefix/testobj.yaml")
        self.assertEqual("testprefix/testobj.yaml", k)

    def test_s3_bucket_name_from_url(self):
        bucket = s3_bucket_name_from_url("https://buk.s3.amazonaws.com/obj.yaml")
        self.assertEqual("buk", bucket)

    def test_fetch_ssm_parameter_value(self):
        # String, no explicit version.
        m_boto_client = mock.Mock()
        m_ssm = mock.Mock()
        m_boto_client.return_value = m_ssm
        m_ssm.get_parameter.return_value = {
            "Parameter": {"Name": "foo", "Type": "String", "Value": "bar", "Version": 1}
        }

        expected = "bar"
        actual = fetch_ssm_parameter_value(m_boto_client, "foo")
        self.assertEqual(expected, actual)

        m_ssm.get_parameter.return_value = {
            "Parameter": {
                "Name": "foo",
                "Type": "StringList",
                "Value": "bar,baz,11",
                "Version": 1,
            }
        }

        expected = "bar,baz,11"
        actual = fetch_ssm_parameter_value(m_boto_client, "foo")
        self.assertEqual(expected, actual)
