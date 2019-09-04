import logging
from pathlib import Path
from typing import List

from taskcat._config import Config
from taskcat._logger import PrintMsg
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


def validate_all_templates(config: Config) -> None:
    _validated_templates: List[Path] = []

    for test in config.tests.values():
        if test.template_file in _validated_templates:
            continue
        try:
            region = test.regions[0]
            test.template.validate(region.name, region.bucket.name)  # type: ignore
            _validated_templates.append(test.template_file)
            LOG.info(
                f"Validated template: {str(test.template_file)}",
                extra={"nametag": PrintMsg.PASS},
            )
        except Exception as e:
            LOG.critical(f"Exception: {str(e)}")
            raise TaskCatException(f"Unable to validate {test.template_file.name}")
