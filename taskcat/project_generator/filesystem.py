import os
from jinja2 import Template
from os import path

TEMPLATES_ROOT_DIR = 'templates'


class FilesystemService:
    def project_templates_root(self, project_type):
        return self._templates_root_path() + os.sep + project_type + os.sep

    def traverse_templates(self, project_type):
        '''
        A wrapper around os.walk that returns the generator to traverse
        the templates directory
        '''
        return os.walk(self.project_templates_root(project_type))

    def create_project_directory(self, project_path):
        os.mkdir(project_path)

    def generate_file(self, content, destination_path):
        '''
        Given the generated content and a destination path, it will
        write that content to a file in that path.
        '''
        with open(destination_path, 'w') as f:
            f.write(content)

    def load_template(self, template_path):
        '''
        Give a full path to a template file it will return a jinja2
        Template object that responds to `render` method taking
        the template parameters
        '''
        with open(template_path) as f:
            return Template(f.read())

    def _templates_root_path(self):
        return (
            path.dirname(path.realpath(__file__)) + os.sep + TEMPLATES_ROOT_DIR
        )
