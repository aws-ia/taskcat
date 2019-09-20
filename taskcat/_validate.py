import logging
from pathlib import Path
from typing import Dict, List

from taskcat._cfn.template import Template
from taskcat._config import Config
from taskcat._logger import PrintMsg
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


def validate_all_templates(
    config: Config, templates: Dict[str, Template], buckets: dict
) -> None:
    # TODO: validation should happen concurrently, recursively and be run against all
    #  test regions
    _validated_templates: List[Path] = []

    for test_name, test in config.config.tests.items():
        if test.template in _validated_templates:
            continue
        try:
            region = test.regions[0] if test.regions else "us-east-1"
            templates[test_name].validate(region, buckets[test_name][region].name)
            _validated_templates.append(test.template)
            LOG.info(
                f"Validated template: {str(test.template)}",
                extra={"nametag": PrintMsg.PASS},
            )
        except Exception as e:
            LOG.debug(f"Exception: {str(e)}", exc_info=True)
            raise TaskCatException(f"Unable to validate {test.template}")
