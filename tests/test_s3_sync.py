import os
import unittest
from pathlib import Path
from unittest import mock

from taskcat._s3_sync import S3Sync


class TestS3Sync(unittest.TestCase):
    def test_init(self):
        m_s3_client = mock.Mock()
        m_s3_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "test_prefix/test_object", "ETag": "test_etag"}]
        }
        m_s3_client.delete_objects.return_value = {}
        m_s3_client.upload_file.return_value = None
        prefix = "test_prefix"
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/").resolve()
        S3Sync(
            m_s3_client,
            "test_bucket",
            prefix,
            str(base_path / "lambda_build_with_submodules"),
        )
        m_s3_client.list_objects_v2.assert_called_once()
        m_s3_client.delete_objects.assert_called_once()
        m_s3_client.upload_file.assert_called()
