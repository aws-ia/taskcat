import sys
import os
import cfnlint
import six
from qs_cfn_lint_rules.stack import StackHelper

master_template_path = sys.argv[1]

try:
    cfn = cfnlint.decode.cfn_yaml.load(master_template_path)
except Exception as e:
    sys.stderr.write("Exception parsing: '{}'".format(master_template_path))
    sys.stderr.write(str(e))
    exit(1)

# print(cfn)


def get_resources(template, resource_type=[]):
    """
        Get Resources
        Filter on type when specified
    """
    resources = template.get('Resources', {})
    if not isinstance(resources, dict):
        return {}
    if isinstance(resource_type, six.string_types):
        resource_type = [resource_type]

    results = {}
    for k, v in resources.items():
        if isinstance(v, dict):
            if (v.get('Type', None) in resource_type) or (not resource_type and v.get('Type') is not None):
                results[k] = v

    return results


def get_mappings(template):
    """Get Mappings"""

    mappings = template.get('Mappings', {})
    if not mappings:
        return {}

    return mappings


try:
    cfn_resources = get_resources(cfn, resource_type=['AWS::CloudFormation::Stack'])
except Exception as a:
    sys.stderr.write("Exception parsing: '{}'".format(master_template_path))
    sys.stderr.write(str(e))
    exit(2)

try:
    cfn_mappings = get_mappings(cfn)
except Exception as a:
    sys.stderr.write("Exception parsing: '{}'".format(master_template_path))
    sys.stderr.write(str(e))
    exit(3)

printed = False
filepath_list = []

try:
    for r_name, r_values in cfn_resources.items():

        properties = r_values.get('Properties')
        child_template_url = properties.get('TemplateURL')
        master_template_path_print = os.path.abspath(master_template_path)

        original = "/mnt/c/Users/gargana/workspace/scratch/qs-code/"
        replacement = "test/fixtures/templates/stackhelper/"
        master_template_path_print = master_template_path_print.replace(original, replacement)
        if not printed:
            printed = True
            print("")
        print("{")
        print("\t\"input\": {")
        print("\t\t\"master_template\": \"" + "{}".format(master_template_path_print) + "\",")
        print("\t\t\"child_template\": \"{}".format(child_template_url) + "\"")
        print("\t},")

        StackHelper.mappings = cfn_mappings

        resolved_template_url_list = StackHelper.flatten_template_url(child_template_url)
        print("\t\"output\":{")
        print("\t\t\"url_paths\": {}".format(resolved_template_url_list).replace("'", '"') + ",")
        filepath_list = []
        for resolved_path in resolved_template_url_list:
            filepath = StackHelper.find_local_child_template(os.path.abspath(master_template_path), str(resolved_path))
            filepath = filepath.replace(original, replacement)
            filepath_list.append(filepath)

        filepath_list = list(dict.fromkeys(filepath_list))
        print("\t\t\"local_paths\": {} ".format(filepath_list).replace("'", '"'))
        print("\t}")
        print("},")

except Exception as e:
    sys.stderr.write("Exception parsing: '{}'".format(master_template_path))
    sys.stderr.write(str(e))
    exit(4)

    # tests = [:
    #     {
    #         "input": {
    #             "master_template": "/mnt/c/Users/gargana/workspace/scratch/qs-code/quickstart-amazon-redshift/templates/redshift-master.template.yaml",
    #             "child_template": "{'Fn::Sub': ['https://${QSS3BucketName}.${QSS3Region}.amazonaws.com/${QSS3KeyPrefix}submodules/quickstart-aws-vpc/templates/aws-vpc.template', {'QSS3Region': {'Fn::If': ['GovCloudCondition', 's3-us-gov-west-1', 's3']}}]}"
    #         },
    #         "output": {
    #             "url_paths": ['/QSS3KeyPrefix/submodules/quickstart-aws-vpc/templates/aws-vpc.template'],
    #             "local_paths": [
    #                 '/mnt/c/Users/gargana/workspace/scratch/qs-code/quickstart-amazon-redshift/submodules/quickstart-aws-vpc/templates/aws-vpc.template']
    #         }
    #     }
    # ]


