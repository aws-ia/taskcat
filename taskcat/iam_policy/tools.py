import boto3
import json

CFN = boto3.client('cloudformation'
                   )
def _get_all_resource_types():
    t = []
    paginator = CFN.get_paginator('list_types')
    for page in paginator.paginate(Visibility='PUBLIC',ProvisioningType='FULLY_MUTABLE',Type='RESOURCE',Filters={'Category':'AWS_TYPES'}):
        for r in page['TypeSummaries']:
            t.append(r['TypeArn'])
    return t

def _get_schema_for_resource_type(resource_type_arn):
    resp = CFN.describe_type(Arn=resource_type_arn)
    return json.loads(resp['Schema'])


def _transform_to_abbreviated_format(schema):
    result = {schema['typeName']:{}}
    for method in ['create', 'read', 'update', 'delete']:
        transformed = []
        for z in schema['handlers'][method]['permissions']:
            if not z:
                continue
            try:
                x, y = z.split(':')
                transformed.append(f"{x.lower()}:{y}")
            except ValueError:
                transformed.append(z)
        result[schema['typeName']][method] = transformed
    return result

