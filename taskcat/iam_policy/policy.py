import json
import logging
from pathlib import Path
from typing import List

import pkg_resources
from taskcat._config import Config

LOG = logging.getLogger(__name__)


class CFNPolicyGenerator:
    def __init__(self, config: Config, output_file: str):
        self._config = config
        self._data_file_path = pkg_resources.resource_filename(
            "taskcat", "/cfg/cfn_resource_iam_policy.json"
        )
        self._output_file = output_file

    def generate_policy(self):
        LOG.warning("This is an ALPHA feature. Use with caution")
        templates = []
        for template in self._config.get_templates().values():
            templates.append(template)
            templates += list(template.descendents)

        resource_types = set()
        for template in templates:
            for _resource_name, _resource in template.template["Resources"].items():
                resource_types.add(_resource["Type"])

        policy = self._policy_from_resource_types(list(resource_types))

        with open(Path(self._output_file).resolve(), "w", encoding="utf-8") as _f:
            _f.write(json.dumps(policy, indent=4, sort_keys=True))

    @staticmethod
    def _generate_placeholder(resource_type_name):
        svc_name = resource_type_name.split("::")[1].lower()
        _x = {
            "create": [f"{svc_name}:*"],
            "read": [f"{svc_name}:*"],
            "update": [f"{svc_name}:*"],
            "delete": [f"{svc_name}:*"],
        }
        return _x

    def _policy_from_resource_types(self, resource_types: List[str]):
        with open(self._data_file_path, encoding="utf-8") as _f:
            data = json.load(_f)

        _policy = {"Version": "2012-10-17", "Statement": []}
        _statements: dict = {
            "create": set(),
            "read": set(),
            "update": set(),
            "delete": set(),
        }

        for resource in resource_types:
            for k, v in data.get(
                resource, self._generate_placeholder(resource)
            ).items():
                for action in v:
                    _statements[k].add(action)

        for k, v in _statements.items():
            _policy["Statement"].append(
                {
                    "Sid": f"{k.upper()}Actions",
                    "Effect": "Allow",
                    "Action": sorted(v),
                    "Resource": "*",
                }
            )
        LOG.warning(
            "NOTE: The generated IAM policy will contain <service>:* IAM Actions where a"
            + " coverage gap exists within the CloudFormation Resource Spec"
        )
        LOG.warning(
            "Provide feedback to the CloudFormation team via: "
            + "https://github.com/aws-cloudformation/cloudformation-coverage-roadmap "
        )
        return _policy
