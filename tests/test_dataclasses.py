import unittest

from dataclasses_jsonschema import ValidationError
from taskcat._dataclasses import ProjectConfig


class TestNewConfig(unittest.TestCase):
    def test_s3_acl_validation(self):
        invalid = ["test", "not-a-canned-acl"]
        valid = [
            "private",
            "public-read",
            "aws-exec-read",
            "public-read-write",
            "authenticated-read",
            "bucket-owner-read",
            "bucket-owner-full-control",
        ]
        for acl in invalid:
            with self.assertRaises(ValidationError):
                ProjectConfig(s3_object_acl=acl).to_json(validate=True)
        for acl in valid:
            p = ProjectConfig(s3_object_acl=acl).to_dict(validate=True)
            self.assertEqual(p["s3_object_acl"], acl)
