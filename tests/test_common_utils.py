import errno
import os
import unittest

import mock

from taskcat._common_utils import (
    get_s3_domain,
    make_dir,
    merge_dicts,
    name_from_stack_id,
    param_list_to_dict,
    pascal_to_snake,
    region_from_stack_id,
    s3_url_maker,
)
from taskcat.exceptions import TaskCatException


class TestCfnLogTools(unittest.TestCase):
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

    def test_s3_url_maker(self):
        m_s3 = mock.Mock()
        m_s3.get_bucket_location.return_value = {"LocationConstraint": None}
        actual = s3_url_maker("test-bucket", "test-key/1", m_s3)

        self.assertEqual("https://test-bucket.s3.amazonaws.com/test-key/1", actual)
        m_s3.get_bucket_location.return_value = {"LocationConstraint": "us-west-2"}

        actual = s3_url_maker("test-bucket", "test-key/1", m_s3)
        self.assertEqual(
            "https://test-bucket.s3-us-west-2.amazonaws.com/test-key/1", actual
        )

    def test_get_s3_domain(self):
        m_ssm = mock.Mock()
        m_ssm.get_parameter.return_value = {"Parameter": {"Value": "aws-cn"}}
        actual = get_s3_domain("test-region", m_ssm)
        self.assertEqual("amazonaws.com.cn", actual)

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
