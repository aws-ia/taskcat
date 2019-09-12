import logging
import random
import string
from pathlib import Path
from typing import Dict, List, Set, Union

import cfnlint
from taskcat._client_factory import Boto3Cache
from taskcat._common_utils import s3_bucket_name_from_url, s3_key_from_url, s3_url_maker
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class Template:
    def __init__(
        self,
        template_path: Union[str, Path],
        project_root: Union[str, Path] = "",
        url: str = "",
        s3_key_prefix: str = "",
        boto3_cache: Boto3Cache = None,
        s3_region: str = "us-east-1",
    ):
        self.boto3_cache = boto3_cache if boto3_cache else Boto3Cache()
        self.s3_region = s3_region
        self.s3_client = self.boto3_cache.session().client("s3", region_name=s3_region)
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

    def _upload(self, bucket_name: str, prefix: str = "") -> str:
        s3_client = self.boto3_cache.client("s3")
        s3_client.upload_file(
            str(self.template_path), bucket_name, prefix + self.template_path.name
        )
        return s3_url_maker(
            bucket_name, f"{prefix}{self.template_path.name}", self.s3_client
        )

    def _delete_s3_object(self, url):
        if not url:
            return
        bucket_name = s3_bucket_name_from_url(url)
        path = s3_key_from_url(url)
        self.s3_client.delete_objects(
            Bucket=bucket_name, Delete={"Objects": [{"Key": path}], "Quiet": True}
        )

    @property
    def s3_key(self):
        suffix = str(self.template_path.relative_to(self.project_root))
        return self._s3_key_prefix + suffix

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

    def _create_temporary_s3_object(self, bucket_name, prefix):
        if self.url:
            return ""
        rand = (
            "".join(random.choice(string.ascii_lowercase) for _ in range(8))  # nosec
            + "/"
        )
        return self._upload(bucket_name, prefix + rand)

    def _do_validate(self, tmpurl, region):
        error = None
        exception = None
        url = tmpurl if tmpurl else self.url
        cfn_client = self.boto3_cache.session().client(
            "cloudformation", region_name=region
        )
        try:
            cfn_client.validate_template(TemplateURL=url)
        except cfn_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "ValidationError":
                exception = e
            error = (
                f"{self.template_path} - {region} - {e.response['Error']['Message']}"
            )
        return error, exception

    def validate(self, region, bucket_name: str = "", prefix: str = ""):
        if not self.url and not bucket_name:
            raise ValueError(
                "validate requires either the url instance variable, or bucket_"
                "name+prefix to be provided"
            )
        tmpurl = self._create_temporary_s3_object(bucket_name, prefix)
        error, exception = self._do_validate(tmpurl, region)
        self._delete_s3_object(tmpurl)
        if exception:
            raise exception
        return error

    def _template_url_to_path(self, template_url):
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
        template_path = self.project_root / template_path
        if template_path.exists():
            return template_path
        LOG.error(
            "Failed to discover path for %s, path %s does not exist",
            template_url,
            template_path,
        )
        return ""

    def _get_relative_url(self, path: str) -> str:
        if not self.url:
            return ""
        suffix = str(self.template_path).replace(str(self.project_root), "")
        suffix_length = len(suffix.lstrip("/").split("/"))
        url_prefix = "/".join(self.url.split("/")[0:-suffix_length])
        suffix = str(path).replace(str(self.project_root), "")
        url = url_prefix + suffix
        return url

    def url_prefix(self) -> str:
        if not self.url:
            return ""
        suffix = str(self.template_path).replace(str(self.project_root), "")
        suffix_length = len(suffix.lstrip("/").split("/"))
        url_prefix = "/".join(self.url.split("/")[0:-suffix_length])
        return url_prefix

    def _find_children(self) -> None:
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
                child_template_instance = Template(
                    child,
                    self.project_root,
                    self._get_relative_url(child),
                    self._s3_key_prefix,
                    self.boto3_cache,
                    self.s3_region,
                )
            self.children.append(child_template_instance)

    @property
    def descendents(self) -> Set["Template"]:
        def recurse(template, descendants):
            descendants = descendants.union(set(template.children))
            for child in template.children:
                descendants = descendants.union(recurse(child, descendants))
            return descendants

        return recurse(self, set())

    def parameters(
        self
    ) -> Dict[str, Union[None, str, int, bool, List[Union[int, str]]]]:
        parameters = {}
        for param_key, param in self.template.get("Parameters", {}).items():
            parameters[param_key] = param.get("Default")
        return parameters
