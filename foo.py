#!/usr/bin/env python
# flake8: noqa
from taskcat.config import Config

c = Config(
    template_path="/Users/andglenn/development/quickstarts/mine/linux-bastion/templates/linux-bastion.template",
    project_config_path="/Users/andglenn/development/quickstarts/mine/linux-bastion/ci/taskcat.yml",
    project_root="/Users/andglenn/development/quickstarts/mine/linux-bastion",
)
