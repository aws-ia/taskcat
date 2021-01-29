import logging
from importlib import import_module
from typing import Mapping, Optional

from taskcat._config import Config
from taskcat._dataclasses import TestObj
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


def execute_hooks(
    stage: str, config: Config, tests: Mapping[str, TestObj], parameters, outputs=None,
):
    prehook_failures = []
    for name, test in config.config.tests.items():
        if getattr(test, stage):
            for hook in getattr(test, stage):
                LOG.warning(f"{stage} is alpha functionality, use with caution.")
                try:
                    plugin = import_module(f"taskcat_plugin_{hook.type}")
                except ModuleNotFoundError as e:
                    raise TaskCatException(f'hook "{hook.type}" not found') from e
                try:
                    LOG.info(f"Executing {stage[:-1]} {hook.type} for test {name}")
                    plugin.Hook(hook.config, config, tests[name], parameters, outputs)  # type: ignore
                except TaskCatException as e:
                    prehook_failures.append((hook.type, name, str(e)))
    if prehook_failures:
        raise TaskCatException(f"One or more hooks failed {prehook_failures}")


class BaseTaskcatHook:
    def __init__(
        self,
        hook_config: dict,
        config: Config,
        test: TestObj,
        parameters: dict,
        outputs: Optional[dict],
    ):
        pass
