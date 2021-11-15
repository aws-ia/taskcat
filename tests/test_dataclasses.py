import unittest
import uuid
from pathlib import Path

from dataclasses_jsonschema import ValidationError
from taskcat._config import Config
from taskcat._dataclasses import ProjectConfig, TestObj
from taskcat.exceptions import TaskCatException


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


class TestTestObj(unittest.TestCase):
    def test_stack_name(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        templates = c.get_templates()
        template = templates["taskcat-json"]

        example_uuid = uuid.uuid4()

        # Assert full stack name
        test_obj = TestObj(
            name="foobar",
            template_path=template.template_path,
            template=template.template,
            project_root=template.project_root,
            regions=[],
            artifact_regions=[],
            tags=[],
            uid=example_uuid,
            _stack_name="foobar-more-coffee",
            _project_name="example-proj",
        )
        expected = "foobar-more-coffee"
        actual = test_obj.stack_name
        self.assertEqual(expected, actual)

        # Assert stack prefix
        test_obj = TestObj(
            name="foobar",
            template_path=template.template_path,
            template=template.template,
            project_root=template.project_root,
            regions=[],
            artifact_regions=[],
            tags=[],
            uid=example_uuid,
            _stack_name_prefix="blah-",
            _project_name="example-proj",
        )
        expected = "blah-example-proj-foobar-{}".format(example_uuid.hex)
        actual = test_obj.stack_name
        self.assertEqual(expected, actual)

        # Assert stack prefix short
        test_obj = TestObj(
            name="foobar",
            template_path=template.template_path,
            template=template.template,
            project_root=template.project_root,
            regions=[],
            artifact_regions=[],
            tags=[],
            uid=example_uuid,
            _stack_name_prefix="blah-",
            _project_name="example-proj",
            _shorten_stack_name=True,
        )
        expected = "blah-foobar-{}".format(example_uuid.hex[:6])
        actual = test_obj.stack_name
        self.assertEqual(expected, actual)

        # Assert stack suffix
        test_obj = TestObj(
            name="foobar",
            template_path=template.template_path,
            template=template.template,
            project_root=template.project_root,
            regions=[],
            artifact_regions=[],
            tags=[],
            uid=example_uuid,
            _stack_name_suffix="asdf",
            _project_name="example-proj",
        )
        expected = "tCaT-example-proj-foobar-asdf"
        actual = test_obj.stack_name
        self.assertEqual(expected, actual)

        # Assert no customizations.
        test_obj = TestObj(
            name="foobar",
            template_path=template.template_path,
            template=template.template,
            project_root=template.project_root,
            regions=[],
            artifact_regions=[],
            tags=[],
            uid=example_uuid,
            _project_name="example-proj",
        )
        expected = f"tCaT-example-proj-foobar-{example_uuid.hex}"
        actual = test_obj.stack_name
        self.assertEqual(expected, actual)

        # Assert only short stack name.
        test_obj = TestObj(
            name="foobar",
            template_path=template.template_path,
            template=template.template,
            project_root=template.project_root,
            regions=[],
            artifact_regions=[],
            tags=[],
            uid=example_uuid,
            _project_name="example-proj",
            _shorten_stack_name=True,
        )
        expected = "tCaT-foobar-{}".format(example_uuid.hex[:6])
        actual = test_obj.stack_name
        self.assertEqual(expected, actual)

    def test_param_combo_assert(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        templates = c.get_templates()
        template = templates["taskcat-json"]

        example_uuid = uuid.uuid4()

        # Assert full stack name
        with self.assertRaises(TaskCatException):
            _ = TestObj(
                name="foobar",
                template_path=template.template_path,
                template=template.template,
                project_root=template.project_root,
                regions=[],
                artifact_regions=[],
                tags=[],
                uid=example_uuid,
                _stack_name="foobar-more-coffee",
                _stack_name_prefix="blah",
                _project_name="example-proj",
            )
        with self.assertRaises(TaskCatException):
            _ = TestObj(
                name="foobar",
                template_path=template.template_path,
                template=template.template,
                project_root=template.project_root,
                regions=[],
                artifact_regions=[],
                tags=[],
                uid=example_uuid,
                _stack_name="foobar-more-coffee",
                _stack_name_suffix="blah",
                _project_name="example-proj",
            )
        with self.assertRaises(TaskCatException):
            _ = TestObj(
                name="foobar",
                template_path=template.template_path,
                template=template.template,
                project_root=template.project_root,
                regions=[],
                artifact_regions=[],
                tags=[],
                uid=example_uuid,
                _stack_name_prefix="foo",
                _stack_name_suffix="blah",
                _project_name="example-proj",
            )
