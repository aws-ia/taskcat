import os
from jinja2 import Template
from os import path

TEMPLATES_ROOT_DIR = 'templates'


def traverse_project_templates(project_type):
    '''
    A wrapper around os.walk that returns the generator to traverse
    the templates directory
    '''
    project_templates_root_path = templates_root_path() + os.sep + project_type
    return os.walk(project_templates_root_path)


def create_project_directory(project_path):
    os.mkdir(project_path)


def generate_file(content, destination_path):
    '''
    Given the generated content and a destination path, it will
    write that content to a file in that path.
    '''
    with open(destination_path, 'w') as f:
        f.write(content)


def load_template(template_path):
    '''
    Give a full path to a template file it will return a jinja2
    Template object that responds to `render` method taking
    the template parameters
    '''
    with open(template_path) as f:
        return Template(f.read())


def templates_root_path():
    return path.dirname(path.realpath(__file__)) + os.sep + TEMPLATES_ROOT_DIR
