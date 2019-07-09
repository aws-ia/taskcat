# TODO delete this file after integrating with cli option parser
#      this is only here to illustrate generator's usage
# run as: python path/to/runner.py <project_destination>
#
# pylint: skip-file

import sys

from taskcat.project_generator import (
    FilesystemService,
    ProjectConfiguration,
    ProjectGenerator,
)

DESTINATION = sys.argv[1]
CONFIG = ProjectConfiguration(
    "owner@example.com", "awesome_quickstart", "quickstart", ["us-east-1", "us-west-2"]
)

ProjectGenerator(CONFIG, DESTINATION, FilesystemService()).generate()
