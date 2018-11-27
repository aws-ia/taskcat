import logging
import os
from collections import namedtuple


def full_path(root, resource):
    return root + os.sep + resource


def template_paths(template_dir, templates):
    return [template_dir + os.sep + t for t in templates]


ProjectConfiguration = namedtuple(
    'ProjectConfiguration',
    'owner_email, project_name, project_type, supported_regions'
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ProjectGenerator:
    def __init__(self, config, destination_directory, filesystem_service):
        logger.info('Initializing with...')
        logger.info('Project configuration: {}'.format(config))
        logger.info('Project destination: {}'.format(destination_directory))
        self.config = config
        self.destination = destination_directory
        self.filesystem = filesystem_service

    def generate(self):
        for directory, _, files in self._traverse_templates():
            project_path = self._full_destination_path(directory)
            self._make_project_directory(project_path)

            template_filepaths = template_paths(directory, files)
            self._generate_project_files(template_filepaths, project_path)

    def _traverse_templates(self):
        return self.filesystem.traverse_templates(self.config.project_type)

    def _full_destination_path(self, path):
        templates_root = self.filesystem.project_templates_root(
            self.config.project_type
        )
        path = path.replace(templates_root, '')
        return full_path(self.destination, path)

    def _make_project_directory(self, project_directory):
        try:
            logger.info('creating {}'.format(project_directory))
            self.filesystem.create_project_directory(project_directory)
        except FileExistsError as e:
            logging.warn("{} - skipping...".format(e))

    def _generate_project_files(self, template_filepaths, project_directory):
        logger.info('generating files...')
        for filepath in template_filepaths:
            template = self.filesystem.load_template(filepath)
            destination_filepath = self._destination_filepath(filepath)
            self.filesystem.generate_file(
                self._render_template_content(template),
                destination_filepath
            )
            logger.info('generated {}'.format(destination_filepath))

    def _destination_filepath(self, filepath):
        destination = self._full_destination_path(filepath)
        return self._remove_template_extension(destination)

    def _remove_template_extension(self, filename):
        return os.path.splitext(filename)[0]

    def _render_template_content(self, template):
        return template.render(config=self.config)
