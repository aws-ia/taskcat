import json

import boto3

CFN = boto3.client("cloudformation")


def _get_all_resource_types():
    _t = []
    paginator = CFN.get_paginator("list_types")
    for page in paginator.paginate(
        Visibility="PUBLIC",
        ProvisioningType="FULLY_MUTABLE",
        Type="RESOURCE",
        Filters={"Category": "AWS_TYPES"},
    ):
        for _r in page["TypeSummaries"]:
            _t.append(_r["TypeArn"])
    return _t


def _get_schema_for_resource_type(resource_type_arn):
    resp = CFN.describe_type(Arn=resource_type_arn)
    return json.loads(resp["Schema"])


def _transform_to_abbreviated_format(schema):
    result = {schema["typeName"]: {}}
    for method in ["create", "read", "update", "delete"]:
        transformed = []
        for _z in schema["handlers"][method]["permissions"]:
            if not _z:
                continue
            try:
                _x, _y = _z.split(":")
                transformed.append(f"{_x.lower()}:{_y}")
            except ValueError:
                transformed.append(_z)
        result[schema["typeName"]][method] = transformed
    return result
