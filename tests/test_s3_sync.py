import json
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

    @mock.patch.object(S3Sync, "_sync", autospec=True)
    @mock.patch.object(S3Sync, "_get_s3_file_list", autospec=True)
    @mock.patch("os.walk", autospec=True)
    def test__get_local_file_list(self, mock_oswalk, _, __):
        with open(Path(__file__).parent / "data/s3sync/oswalk_output.json") as f:
            oswalk_results = json.load(f)
        with open(
            Path(__file__).parent / "data/s3sync/s3sync_local_file_list_expected.json"
        ) as f:
            expected_results = json.load(f)

        mock_oswalk.return_value = oswalk_results

        m_s3_client = mock.Mock()

        prefix = "test_prefix"
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/").resolve()
        s3s = S3Sync(
            m_s3_client,
            "test_bucket",
            prefix,
            str(base_path / "lambda_build_with_submodules"),
            dry_run=True,
        )
        actual_results = s3s._get_local_file_list("/tmp/repo", False)

        self.assertEqual(expected_results, actual_results)
