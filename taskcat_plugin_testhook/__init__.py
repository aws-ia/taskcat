from typing import Mapping, Optional

from taskcat._config import Config
from taskcat._dataclasses import TestObj
from taskcat.exceptions import TaskCatException
from taskcat.testing._hooks import BaseTaskcatHook


class Hook(BaseTaskcatHook):
    def __init__(
        self,
        hook_config: dict,
        config: Config,
        tests: Mapping[str, TestObj],
        parameters: dict,
        outputs: Optional[dict],
    ):
        super().__init__(hook_config, config, tests, parameters, outputs)
        if hook_config.get("generate_failure"):
            raise TaskCatException("generated failure from hook")
