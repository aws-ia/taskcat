import logging
from pathlib import Path
from typing import Dict, List, Union

import cfnlint
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class Template:
    def __init__(
        self,
        template_path: Union[str, Path],
        project_root: Union[str, Path] = "",
        url: str = "",
        s3_key_prefix: str = "",
    ):
        self.template_path: Path = Path(template_path).expanduser().resolve()
        self.template = cfnlint.decode.cfn_yaml.load(str(self.template_path))
        with open(template_path, "r") as file_handle:
            self.raw_template = file_handle.read()
        project_root = (
            project_root if project_root else self.template_path.parent.parent
        )
        self.project_root = Path(project_root).expanduser().resolve()
        self.url = url
        self._s3_key_prefix = s3_key_prefix
        self.children: List[Template] = []
        self._find_children()

    def __str__(self):
        return str(self.template)

    def __repr__(self):
        return f"<Template {self.template_path} at {hex(id(self))}>"

    @property
    def s3_key(self):
        suffix = str(self.template_path.relative_to(self.project_root).as_posix())
        return self._s3_key_prefix + suffix

    @property
    def s3_key_prefix(self):
        return self._s3_key_prefix

    @property
    def linesplit(self):
        return self.raw_template.split("\n")

    def write(self):
        """writes raw_template back to file, and reloads decoded template, useful if
        the template has been modified"""
        with open(str(self.template_path), "w") as file_handle:
            file_handle.write(self.raw_template)
        self.template = cfnlint.decode.cfn_yaml.load(self.template_path)
        self._find_children()

    def _template_url_to_path(self, template_url):
        # TODO: this code assumes a specific url schema, should rather attempt to
        #  resolve values from params/defaults
        template_path = None
        if isinstance(template_url, dict):
            if "Fn::Sub" in template_url.keys():
                if isinstance(template_url["Fn::Sub"], str):
                    template_path = template_url["Fn::Sub"].split("}")[-1]
                else:
                    template_path = template_url["Fn::Sub"][0].split("}")[-1]
            elif "Fn::Join" in list(template_url.keys())[0]:
                template_path = template_url["Fn::Join"][1][-1]
        elif isinstance(template_url, str):
            template_path = "/".join(template_url.split("/")[-2:])
        if isinstance(template_path, str):
            template_path = self.project_root / template_path
            if template_path.is_file():
                return template_path
        LOG.warning(
            "Failed to discover path for %s, path %s does not exist",
            template_url,
            template_path,
        )
        return ""

    def _get_relative_url(self, path: str) -> str:
        suffix = str(path).replace(str(self.project_root), "")
        url = self.url_prefix() + suffix
        return url

    def url_prefix(self) -> str:
        if not self.url:
            return ""
        suffix = str(self.template_path).replace(str(self.project_root), "")
        suffix_length = len(suffix.lstrip("/").split("/"))
        url_prefix = "/".join(self.url.split("/")[0:-suffix_length])
        return url_prefix

    def _find_children(self) -> None:  # noqa: C901
        children = set()
        if "Resources" not in self.template:
            raise TaskCatException(
                f"did not receive a valid template: {self.template_path} does not "
                f"have a Resources section"
            )
        for resource in self.template["Resources"].keys():
            resource = self.template["Resources"][resource]
            if resource["Type"] == "AWS::CloudFormation::Stack":
                child_name = self._template_url_to_path(
                    resource["Properties"]["TemplateURL"]
                )
                if child_name:
                    children.add(child_name)
        for child in children:
            child_template_instance = None
            for descendent in self.descendents:
                if str(descendent.template_path) == str(child):
                    child_template_instance = descendent
            if not child_template_instance:
                try:
                    child_template_instance = Template(
                        child,
                        self.project_root,
                        self._get_relative_url(child),
                        self._s3_key_prefix,
                    )
                except Exception:  # pylint: disable=broad-except
                    LOG.debug("Traceback:", exc_info=True)
                    LOG.error(f"Failed to add child template {child}")
            if isinstance(child_template_instance, Template):
                self.children.append(child_template_instance)

    @property
    def descendents(self) -> List["Template"]:
        desc_map = {}

        def recurse(template):
            for child in template.children:
                desc_map[str(child.template_path)] = child
                recurse(child)

        recurse(self)

        return list(desc_map.values())

    def parameters(
        self,
    ) -> Dict[str, Union[None, str, int, bool, List[Union[int, str]]]]:
        parameters = {}
        for param_key, param in self.template.get("Parameters", {}).items():
            parameters[param_key] = param.get("Default")
        return parameters
