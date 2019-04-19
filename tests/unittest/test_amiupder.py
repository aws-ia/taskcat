import unittest
import logging
import json
import tempfile
import re
import yaml
import os
import sys
logger = logging.getLogger("taskcat")

class TestAMIUpdater(unittest.TestCase):

    def _module_loader(self):
        try:
            del sys.modules['taskcat.amiupdater']
        except KeyError:
            pass
        from taskcat.amiupdater import AMIUpdater, AMIUpdaterException, ClientFactory
        return AMIUpdater, AMIUpdaterException, ClientFactory

    generic_skeleton_template = {
        "Mappings":{
            "AWSAMIRegionMap":{
                "us-east-1":{
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG":"FOOBAR",
                    "NON_STANDARD_TEST":"FOOBAR"
                },
                "us-east-2":{
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG":"FOOBAR",
                    "NON_STANDARD_TEST":"FOOBAR"
                },
                "us-west-1":{
                        "AMZNLINUXHVM": "FOOBAR",
                        "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                        "NON_STANDARD_TEST": "FOOBAR"
                },
                "us-west-2":{
                        "AMZNLINUXHVM": "FOOBAR",
                        "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                        "NON_STANDARD_TEST": "FOOBAR"
                }
            }
        }
    }

    inline_skeleton_template = {
        "Metadata":{
            "AWSAMIRegionMap":{
                "Filters":{
                    "NON_STANDARD_TEST":{
                        "name": "amzn-ami-hvm-????.??.?.*-x86_64-gp2",
                        "owner-alias": "amazon"
                    }
                }
             }
        },
        "Mappings":{
            "AWSAMIRegionMap":{
                "us-east-1":{
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG":"FOOBAR",
                    "NON_STANDARD_TEST":"FOOBAR"
                },
                "us-east-2":{
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG":"FOOBAR",
                    "NON_STANDARD_TEST":"FOOBAR"
                },
                "us-west-1":{
                        "AMZNLINUXHVM": "FOOBAR",
                        "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                        "NON_STANDARD_TEST": "FOOBAR"
                },
                "us-west-2":{
                        "AMZNLINUXHVM": "FOOBAR",
                        "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                        "NON_STANDARD_TEST": "FOOBAR"
                }
            }
        }
    }

    no_mapping_skeleton_template = {
        "Mappings":{
            "AWSAMIRegionMap":{
                "us-east-1":{
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG":"FOOBAR",
                    "NON_STANDARD_TEST":"FOOBAR"
                },
                "us-east-2":{
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG":"FOOBAR",
                    "NON_STANDARD_TEST":"FOOBAR"
                },
                "us-west-1":{
                        "AMZNLINUXHVM": "FOOBAR",
                        "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                        "NON_STANDARD_TEST": "FOOBAR"
                },
                "us-west-2":{
                        "AMZNLINUXHVM": "FOOBAR",
                        "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                        "NON_STANDARD_TEST": "FOOBAR"
                }
            }
        }
    }

    invalid_region_skeleton_template = {
            "Mappings":{
                "AWSAMIRegionMap":{
                    "ASKDJSALKD":{
                        "AMZNLINUXHVM": "FOOBAR",
                        "AMZNLINUXHVM_CUSTOM_CONFIG":"FOOBAR",
                        "NON_STANDARD_TEST":"FOOBAR"
                    },
                    "us-east-2":{
                        "AMZNLINUXHVM": "FOOBAR",
                        "AMZNLINUXHVM_CUSTOM_CONFIG":"FOOBAR",
                        "NON_STANDARD_TEST":"FOOBAR"
                    },
                    "us-west-1":{
                            "AMZNLINUXHVM": "FOOBAR",
                            "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                            "NON_STANDARD_TEST": "FOOBAR"
                    },
                    "us-west-2":{
                            "AMZNLINUXHVM": "FOOBAR",
                            "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                            "NON_STANDARD_TEST": "FOOBAR"
                    }
                }
            }
        }

    ami_regex_pattern = re.compile("ami-([0-9a-z]{8}|[0-9a-z]{17})")

    def create_ephemeral_template(self, template_type="generic"):
        if template_type == "generic":
            data = self.generic_skeleton_template
        elif template_type == "inline":
            data = self.inline_skeleton_template
        elif template_type == "no_mapping":
            data = self.no_mapping_skeleton_template
        elif template_type == "invalid_region":
            data = self.invalid_region_skeleton_template

        fd, file = tempfile.mkstemp()
        with open(file, 'w') as f:
            f.write(json.dumps(data))
        os.close(fd)
        return file

    def load_modified_template(self, fn):
        with open(fn) as f:
            t = f.read()
        return json.loads(t)

    def test_upstream_config_ALAMI(self):
        au, AMIUpdaterException, cfactory = self._module_loader()
        cf = cfactory(aws_access_key_id=os.environ['AKEY'], aws_secret_access_key=os.environ['SKEY'])
        mapping_name = "AMZNLINUXHVM"
        template_file = self.create_ephemeral_template()
        amiupdater_args = {
            "path_to_templates": template_file,
            "client_factory": cf
        }
        a = au(**amiupdater_args)
        a.update_amis()


        template_result = self.load_modified_template(template_file)
        for region, mapping_data in template_result["Mappings"]["AWSAMIRegionMap"].items():
            for codename, ami_id in mapping_data.items():
                if codename == mapping_name:
                    with self.subTest(i="Verifying Updated AMI: [{}] / [{}]".format(mapping_name, region)):
                        self.assertRegex(ami_id, self.ami_regex_pattern)

    def test_local_config_ALAMI(self):
        au, AMIUpdaterException, cfactory = self._module_loader()
        cf = cfactory(aws_access_key_id=os.environ['AKEY'], aws_secret_access_key=os.environ['SKEY'])
        config_file_dict = {
            "global":{
                "AMIs":{
                    "AMZNLINUXHVM_CUSTOM_CONFIG":{
                        "name": "amzn-ami-hvm-????.??.?.*-x86_64-gp2",
                        "owner-alias": "amazon"
                    }
                }
            }
        }
        user_config_file = tempfile.mkstemp()[1]
        with open(user_config_file, 'w') as f:
            f.write(yaml.dump(config_file_dict))
        mapping_name = "AMZNLINUXHVM_CUSTOM_CONFIG"
        template_file = self.create_ephemeral_template()

        amiupdater_args = {
            "use_upstream_mappings": False,
            "path_to_templates": template_file,
            "user_config_file": user_config_file,
            "client_factory": cf
        }
        a = au(**amiupdater_args)
        a.update_amis()

        template_result = self.load_modified_template(template_file)
        for region, mapping_data in template_result["Mappings"]["AWSAMIRegionMap"].items():
            for codename, ami_id in mapping_data.items():
                if codename == mapping_name:
                    with self.subTest(i="Verifying Updated AMI: [{}] / [{}]".format(mapping_name, region)):
                        self.assertRegex(ami_id, self.ami_regex_pattern)

    def test_in_template_ALAMI(self):
        au, AMIUpdaterException, cfactory = self._module_loader()
        cf = cfactory(aws_access_key_id=os.environ['AKEY'], aws_secret_access_key=os.environ['SKEY'])
        mapping_name = "NON_STANDARD_TEST"
        template_file = self.create_ephemeral_template(template_type="inline")
        amiupdater_args = {
            "path_to_templates": template_file,
            "use_upstream_mappings": False,
            "client_factory": cf
        }
        a = au(**amiupdater_args)
        a.update_amis()

        template_result = self.load_modified_template(template_file)
        for region, mapping_data in template_result["Mappings"]["AWSAMIRegionMap"].items():
            for codename, ami_id in mapping_data.items():
                if codename == mapping_name:
                    with self.subTest(i="Verifying Updated AMI: [{}] / [{}]".format(mapping_name, region)):
                        self.assertRegex(ami_id, self.ami_regex_pattern)

    def test_invalid_region_exception(self):
        au, AMIUpdaterException, cfactory = self._module_loader()
        cf = cfactory(aws_access_key_id=os.environ['AKEY'], aws_secret_access_key=os.environ['SKEY'])
        template_file = self.create_ephemeral_template(template_type="invalid_region")
        amiupdater_args = {
            "path_to_templates": template_file,
            "use_upstream_mappings": False,
            "client_factory": cf
        }
        a = au(**amiupdater_args)

        self.assertRaises(AMIUpdaterException, a.update_amis)

    def test_no_filters_exception(self):
        au, AMIUpdaterException, cfactory = self._module_loader()
        cf = cfactory(aws_access_key_id=os.environ['AKEY'], aws_secret_access_key=os.environ['SKEY'])
        template_file = self.create_ephemeral_template()
        amiupdater_args = {
            "path_to_templates": template_file,
            "use_upstream_mappings": False,
            "client_factory": cf
        }
        a = au(**amiupdater_args)
        self.assertRaises(AMIUpdaterException, a.update_amis)
