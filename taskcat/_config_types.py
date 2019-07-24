import logging
from pathlib import Path
from typing import Dict, Optional, Union

import yaml
from jsonschema import exceptions

# from taskcat._cfn.template import Template
from taskcat._client_factory import ClientFactory
from taskcat._common_utils import absolute_path, schema_validate as validate
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class Test:
    def __init__(
        self,
        template_file: Path,
        name: str = "default",
        parameter_input: Path = None,
        parameters: dict = None,
        regions: set = None,
        project_root: Union[Path, str] = "./",
        auth: dict = None,
    ):
        auth = auth if auth is not None else {}
        self._project_root: Path = Path(project_root)
        self.template_file: Path = self._guess_path(template_file)
        self.parameter_input_file: Optional[Path] = None
        if parameter_input:
            self.parameter_input_file = self._guess_path(parameter_input)
        self.parameters: Dict[
            str, Union[str, int, bool]
        ] = self._params_from_file() if parameter_input else {}
        if parameters:
            self.parameters.update(parameters)
        validate(self.parameters, "overrides")
        self.regions: list = list(regions) if regions else []
        self.auth: dict = auth
        self.client_factory: ClientFactory = ClientFactory()
        self.name: str = name

    def _guess_path(self, path):
        abs_path = absolute_path(path)
        if not abs_path:
            abs_path = absolute_path(self._project_root / path)
        if not abs_path:
            abs_path = self._legacy_path_prefix(path)
        if not abs_path:
            raise TaskCatException(
                f"Cannot find {path} with project root" f" {self._project_root}"
            )
        return abs_path

    def _legacy_path_prefix(self, path):
        abs_path = absolute_path(self._project_root / "templates" / path)
        if abs_path:
            LOG.warning(
                "found path with deprecated relative path, support for this will be "
                "removed in future versions, please update %s to templates/%s",
                path,
                path,
            )
            return abs_path
        abs_path = absolute_path(self._project_root / "ci" / path)
        if abs_path:
            LOG.warning(
                "found path with deprecated relative path, support for this will be "
                "removed in future versions, please update %s to ci/%s",
                path,
                path,
            )
        return abs_path

    def _params_from_file(self):
        if not self.parameter_input_file:
            return None
        params = yaml.safe_load(open(str(self.parameter_input_file), "r"))
        self._validate_params(params)
        try:
            validate(params, "legacy_parameters")
            params = self._convert_legacy_params(params)
        except exceptions.ValidationError:
            pass
        return params

    @staticmethod
    def _convert_legacy_params(legacy_params):
        return {p["ParameterKey"]: p["ParameterValue"] for p in legacy_params}

    def _validate_params(self, params):
        try:
            validate(params, "overrides")
        except exceptions.ValidationError as e:
            try:
                validate(params, "legacy_parameters")
                LOG.warning(
                    "%s parameters are in a format that will be deprecated in "
                    "the next version of taskcat",
                    str(self.parameter_input_file),
                )
            except exceptions.ValidationError:
                # raise original exception
                raise e

    @classmethod
    def from_dict(cls, raw_test: dict, project_root="./"):
        raw_test["project_root"] = Path(project_root)
        return Test(**raw_test)


class S3BucketConfig:
    def __init__(self, public: bool = False, auto: bool = False, name=""):
        self.region = None
        self.name = name
        self.account = None
        self.client = None
        self.public = public
        self.auto = auto


class AWSRegionObject:
    def __init__(self, region_name: str):
        self.name = region_name
        self.client = None
        self.s3bucket = None

    def __repr__(self):
        return f"<AWSRegionObject(region_name={self.name}) object at {hex(id(self))}>"
