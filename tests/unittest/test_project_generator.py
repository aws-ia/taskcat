from jinja2 import Template
from unittest import TestCase
from unittest.mock import call, Mock
from taskcat.project_generator import (full_path,
                                       ProjectConfiguration,
                                       ProjectGenerator)

TEST_OWNER = 'owner@example.com'
TEST_PROJECT_NAME = 'awesome_new_project'
TEST_PROJECT_TYPE = 'quickstart'
TEST_PROJECT_REGIONS = ['us-west-2', 'us-east-1']
TEST_TEMPLATES_ROOT = './'
TEST_DESTINATION = '/tmp/new_project'


class TestProjectGenerator(TestCase):
    def setUp(self):
        self.mocked_templates = {
            './README.md.jinja': '### {{ config.name }}',
            './ci/taskcat-autobucket.yml.jinja': 'project {{ config.name }}',
            './template/some-template.json.jinja': 'owner {{ config.owner }}',
            './nested/dir/some-file.txt.jinja': '{{ config.project_type }}'
        }

    def test_generate_project(self):
        mock_filesystem_service = self._mock_filesystem_service()
        ProjectGenerator(
            self._quickstart_configuration(),
            TEST_DESTINATION,
            mock_filesystem_service
        ).generate()
        self._verify_filesystem_calls(mock_filesystem_service)

    def _quickstart_configuration(self):
        return ProjectConfiguration(
            TEST_OWNER,
            TEST_PROJECT_NAME,
            TEST_PROJECT_TYPE,
            TEST_PROJECT_REGIONS
        )

    def _mock_filesystem_service(self):
        mock_fs = Mock()
        mock_fs.project_templates_root.return_value = TEST_TEMPLATES_ROOT
        mock_fs.traverse_templates.return_value = self._mocked_template_list()
        mock_fs.create_project_directory.return_value = None
        mock_fs.load_template.side_effect = self._load_template
        mock_fs.generate_file.return_value = None
        return mock_fs

    def _mocked_template_list(self):
        return [
            ('.', None, ['README.md.jinja']),
            ('./ci', None, ['taskcat-autobucket.yml.jinja']),
            ('./template', None, ['some-template.json.jinja']),
            ('./nested', None, []),
            ('./nested/dir', None, ['some-file.txt.jinja'])
        ]

    def _load_template(self, template):
        return Template(self.mocked_templates[template])

    def _verify_filesystem_calls(self, fs_mock):
        self._verify_create_project_directory_calls(fs_mock)
        self._verify_load_template_calls(fs_mock)
        self._verify_generate_file_calls(fs_mock)

    def _verify_create_project_directory_calls(self, fs_mock):
        directories = [t[0] for t in self._mocked_template_list()]
        destinations = [self._resolve_destination(d) for d in directories]
        calls = [call(dest) for dest in destinations]
        fs_mock.create_project_directory.has_calls(calls)

    def _resolve_destination(self, dest):
        return full_path(
            TEST_DESTINATION,
            dest.replace(TEST_TEMPLATES_ROOT, '')
        )

    def _verify_load_template_calls(self, fs_mock):
        calls = [call(template) for template in self.mocked_templates.keys()]
        fs_mock.load_template.has_calls(calls)

    def _verify_generate_file_calls(self, fs_mock):
        calls = [
            self._create_generate_call(k, v) for k, v
            in self.mocked_templates.items()
        ]
        fs_mock.generate_file.has_calls(calls)

    def _create_generate_call(self, path, content):
        filepath = self._resolve_destination(path)
        content = content.replace('{{ config.name }}', TEST_PROJECT_NAME)
        content = content.replace('{{ config.owner }}', TEST_OWNER)
        content = content.replace('{{ config.project_type }}', TEST_PROJECT_TYPE)
        return call(filepath, content)
