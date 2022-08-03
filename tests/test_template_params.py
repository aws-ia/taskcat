import copy
import logging
import os
import re
import unittest
from collections import namedtuple
from io import BytesIO
from pathlib import Path
from unittest import mock

from taskcat._client_factory import Boto3Cache
from taskcat._template_params import ParamGen
from taskcat.exceptions import TaskCatException

logger = logging.getLogger("taskcat")


def client_factory_instance():
    with mock.patch.object(Boto3Cache, "__init__", return_value=None):
        aws_clients = Boto3Cache(None)
    aws_clients._credential_sets = {"default": [None, None, None, None]}
    aws_clients.logger = logger
    return aws_clients


class MockSingleAZClient:
    def __init__(self, *args, **kwargs):
        self.describe_az_output = {
            "AvailabilityZones": [
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1a",
                    "ZoneId": "use1-az6",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1b",
                    "ZoneId": "use1-az5",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1c",
                    "ZoneId": "use1-az4",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1d",
                    "ZoneId": "use1-az3",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1e",
                    "ZoneId": "use1-az2",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1f",
                    "ZoneId": "use1-az1",
                },
            ]
        }
        self.describe_az_output["AvailabilityZones"] = [
            self.describe_az_output["AvailabilityZones"][0]
        ]

    def describe_availability_zones(self, Filters):
        outp = self.describe_az_output
        return outp

    def get_caller_identity(self):
        return {"Account": "0123456789"}

    def get_object(self, Key, **kwargs):
        objresp = {"Body": BytesIO("unicorns".encode("utf-8"))}
        return objresp


class MockClient:
    def __init__(self, *args, **kwargs):
        self.describe_az_output = {
            "AvailabilityZones": [
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1a",
                    "ZoneId": "use1-az6",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1b",
                    "ZoneId": "use1-az5",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1c",
                    "ZoneId": "use1-az4",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1d",
                    "ZoneId": "use1-az3",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1e",
                    "ZoneId": "use1-az2",
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1f",
                    "ZoneId": "use1-az1",
                },
            ]
        }

    def describe_availability_zones(self, Filters):
        outp = self.describe_az_output
        return outp

    def get_caller_identity(self):
        return {"Account": "0123456789"}

    def get_object(self, Key, **kwargs):
        objresp = {"Body": BytesIO("unicorns".encode("utf-8"))}
        return objresp


class TestParamGen(unittest.TestCase):
    class_kwargs = {
        "project_root": Path("."),
        "param_dict": {},
        "bucket_name": "tcat-tag-skdfklsdfklsjf",
        "region": "us-east-1",
        "project_name": "foobar",
        "test_name": "testy_mc_testerson",
        "boto_client": client_factory_instance(),
    }
    rp_namedtup = namedtuple("RegexTestPattern", "test_string test_pattern_attribute")
    regex_patterns = [
        rp_namedtup(
            test_string="$[taskcat_getaz_2]", test_pattern_attribute="RE_GENAZ"
        ),
        rp_namedtup(
            test_string="$[taskcat_genaz_2]", test_pattern_attribute="RE_GENAZ"
        ),
        rp_namedtup(
            test_string="$[taskcat_random-numbers]", test_pattern_attribute="RE_GENNUMB"
        ),
        rp_namedtup(
            test_string="$[taskcat_random-string]",
            test_pattern_attribute="RE_GENRANDSTR",
        ),
        rp_namedtup(
            test_string="test-path-$[taskcat_random-numbers]-suffix",
            test_pattern_attribute="RE_GENNUMB",
        ),
        rp_namedtup(
            test_string="test-path-$[taskcat_random-string]-suffix",
            test_pattern_attribute="RE_GENRANDSTR",
        ),
        rp_namedtup(
            test_string="$[taskcat_autobucket]",
            test_pattern_attribute="RE_GENAUTOBUCKET",
        ),
        rp_namedtup(
            test_string="$[taskcat_autobucket_prefix]",
            test_pattern_attribute="RE_GENAUTOBUCKETPREFIX",
        ),
        rp_namedtup(
            test_string="$[taskcat_current_region]",
            test_pattern_attribute="RE_CURRENT_REGION",
        ),
        rp_namedtup(
            test_string="https://s3.amazonaws.com/$[taskcat_autobucket]/myproject/",
            test_pattern_attribute="RE_GENAUTOBUCKET",
        ),
        rp_namedtup(
            test_string="$[taskcat_genpass_20]", test_pattern_attribute="RE_GENPW"
        ),
        rp_namedtup(
            test_string="$[taskcat_genpass_20]", test_pattern_attribute="RE_COUNT"
        ),
        rp_namedtup(
            test_string="$[taskcat_genpass_20A]", test_pattern_attribute="RE_PWTYPE"
        ),
        rp_namedtup(
            test_string="$[taskcat_gensingleaz_4]",
            test_pattern_attribute="RE_GENAZ_SINGLE",
        ),
        rp_namedtup(
            test_string="$[taskcat_getsingleaz_4]",
            test_pattern_attribute="RE_GENAZ_SINGLE",
        ),
        rp_namedtup(
            test_string="$[taskcat_getkeypair]", test_pattern_attribute="RE_QSKEYPAIR"
        ),
        rp_namedtup(
            test_string="$[taskcat_getlicensebucket]",
            test_pattern_attribute="RE_QSLICBUCKET",
        ),
        rp_namedtup(
            test_string="$[taskcat_getmediabucket]",
            test_pattern_attribute="RE_QSMEDIABUCKET",
        ),
        rp_namedtup(
            test_string="$[taskcat_getlicensecontent]",
            test_pattern_attribute="RE_GETLICCONTENT",
        ),
        rp_namedtup(
            test_string="$[taskcat_presignedurl],bucket,key,100",
            test_pattern_attribute="RE_GETPRESIGNEDURL",
        ),
        rp_namedtup(
            test_string="$[taskcat_getval_foo]", test_pattern_attribute="RE_GETVAL"
        ),
        rp_namedtup(
            test_string="$[taskcat_genuuid]", test_pattern_attribute="RE_GENUUID"
        ),
        rp_namedtup(
            test_string="$[taskcat_genguid]", test_pattern_attribute="RE_GENUUID"
        ),
        rp_namedtup(
            test_string="$[taskcat_url_http://example.com]",
            test_pattern_attribute="RE_GETURL",
        ),
        rp_namedtup(
            test_string="$[taskcat_ssm_/aws/foo/bar/blah]",
            test_pattern_attribute="RE_SSM_PARAMETER",
        ),
        rp_namedtup(
            test_string="$[taskcat_secretsmanager_arn:aws:blah]",
            test_pattern_attribute="RE_SECRETSMANAGER_PARAMETER",
        ),
        rp_namedtup(
            test_string="$[taskcat_project_name]",
            test_pattern_attribute="RE_PROJECT_NAME",
        ),
        rp_namedtup(
            test_string="$[taskcat_test_name]", test_pattern_attribute="RE_TEST_NAME"
        ),
        rp_namedtup(
            test_string="$[taskcat_git_branch]", test_pattern_attribute="RE_GITBRANCH"
        ),
    ]

    def test_regxfind(self):
        pg = ParamGen(**self.class_kwargs)
        re_object = re.compile("foo")
        self.assertEqual(pg.regxfind(re_object, "aslkjfafoo"), "foo")

    def test_regular_expressions(self):
        for i in self.regex_patterns:
            with self.subTest(i=i):
                self.assertRegex(
                    i.test_string, getattr(ParamGen, i.test_pattern_attribute)
                )

    def test_special_regular_expression(self):
        pg = ParamGen(**self.class_kwargs)
        self.assertEqual(pg.regxfind(ParamGen.RE_COUNT, "$[taskcat_getaz_2]"), "2")
        self.assertEqual(pg.regxfind(ParamGen.RE_COUNT, "$[taskcat_genpass_8]"), "8")

    def test_get_available_azs_with_excludes(self):
        class_kwargs = {**self.class_kwargs, "az_excludes": {"use1-az6", "use1-az5"}}
        pg = ParamGen(**class_kwargs)
        pg._boto_client = MockClient
        returned_azs = pg.get_available_azs(4)
        returned_az_list = returned_azs.split(",")
        test_criteria = [
            # tuple (first_param, second_param, test_description)
            (len(returned_az_list), 4, "Verifying we return 4 AZs"),
            (len(set(returned_az_list)), 4, "Verifying we return 4 *unique* AZs"),
            (
                ("us-east-1a" not in returned_az_list),
                True,
                "Verifying us-east-1a is not returned.",
            ),
            (
                ("us-east-1b" not in returned_az_list),
                True,
                "Verifying us-east-1b is not returned.",
            ),
        ]
        for first_param, second_param, test_desc in test_criteria:
            with self.subTest(test_desc):
                self.assertEqual(first_param, second_param)

    def test_get_available_azs(self):
        pg = ParamGen(**self.class_kwargs)
        pg._boto_client = MockClient
        returned_azs = pg.get_available_azs(2)
        returned_az_list = returned_azs.split(",")
        test_criteria = [
            # tuple (first_param, second_param, test_description)
            (len(returned_az_list), 2, "Verifying we return 2 AZs"),
            (len(set(returned_az_list)), 2, "Verifying we return 2 *unique* AZs"),
        ]
        for first_param, second_param, test_desc in test_criteria:
            with self.subTest(test_desc):
                self.assertEqual(first_param, second_param)

    def test_genaz_raises_taskcat_exception(self):
        pg = ParamGen(**self.class_kwargs)
        pg._boto_client = MockSingleAZClient
        with self.assertRaises(TaskCatException):
            pg.get_available_azs(2)

    def test_get_content(self):
        pg = ParamGen(**self.class_kwargs)
        pg._boto_client = MockClient
        self.assertEqual(
            pg.get_content(bucket="unit-test-bucket", object_key="unit-test-key"),
            "unicorns",
        )

    def test_genpassword_type(self):
        pg = ParamGen(**self.class_kwargs)
        genpassword_criteria = [
            # A tuple of (func_call, length, flags, re.Pattern, description)
            (
                pg.genpassword,
                15,
                None,
                re.compile("[0-9A-Za-z]"),
                "Testing a 15 character password. Default PW type",
            ),
            (
                pg.genpassword,
                15,
                "S",
                re.compile(r"[!#\$&{\*:\[=,\]-_%@\+a-zA-Z0-9]+"),
                "Testing a 15 character password, Special Characters Type",
            ),
            (
                pg.genpassword,
                15,
                "A",
                re.compile("[0-9A-Za-z]"),
                "Testing a 15 character password, Alphanumeric Character Type",
            ),
        ]
        for func_call, pwlen, pwflags, re_pattern, test_desc in genpassword_criteria:
            with self.subTest(test_desc):
                self.assertRegex(func_call(pwlen, pwflags), re_pattern)

    def test_genpassword_length(self):
        pg = ParamGen(**self.class_kwargs)
        self.assertEqual(len(pg.genpassword(15)), 15)

    def test_gen_rand_str_regex(self):
        genstr = ParamGen._gen_rand_str(24)
        self.assertRegex(genstr, re.compile("[a-z]"))

    def test_gen_rand_str_len(self):
        genstr = ParamGen._gen_rand_str(33)
        self.assertEqual(len(genstr), 33)

    def test_gen_rand_num(self):
        genstr = ParamGen._gen_rand_num(24)
        self.assertRegex(genstr, re.compile("[0-9]"))

    def test_gen_rand_num_len(self):
        genstr = ParamGen._gen_rand_num(78)
        self.assertEqual(len(genstr), 78)

    def test_gen_uuid_is_string(self):
        pg = ParamGen(**self.class_kwargs)
        generated_uuid = pg._gen_uuid()
        self.assertEqual(type(generated_uuid), type(str()))

    def test_gen_uuid_matches_regex(self):
        pg = ParamGen(**self.class_kwargs)
        generated_uuid = pg._gen_uuid()
        self.assertRegex(
            generated_uuid,
            re.compile("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
        )

    def test_all_regexes_tested(self):
        regex_type = type(re.compile(""))
        tested_expressions = {x.test_pattern_attribute for x in self.regex_patterns}
        all_expressions = {
            x for x in dir(ParamGen) if type(getattr(ParamGen, x)) == regex_type
        }
        self.assertEqual(all_expressions, tested_expressions)

    def test_param_value_none_raises_exception(self):
        params = copy.deepcopy(self.class_kwargs)
        params["param_dict"] = {"Foo": None}
        with self.assertRaises(TaskCatException):
            _ = ParamGen(**params)

    def test_regex_replace_param_value(self):
        pg = ParamGen(**self.class_kwargs)
        pg.param_name = "test_param"
        pg.param_value = "example-foo-value"
        re_pattern = re.compile("foo")
        pg._regex_replace_param_value(re_pattern, "bar")
        self.assertEqual(pg.param_value, "example-bar-value")

    def test_convert_to_str(self):
        pg = ParamGen(**self.class_kwargs)
        pg.param_name = "test_param"
        pg.param_value = 1234
        pg.convert_to_str()
        self.assertEqual(pg.param_value, "1234")

    def test_param_transform(self):  # noqa: C901
        input_params = {
            "AvailabilityZones": "$[taskcat_genaz_3]",
            "ByteValue": "1",
            "GlobalOverrideTest": "override",
            "LocalOverrideTest": "override",
            "PasswordA": "$[taskcat_genpass_8A]",
            "PasswordAConfirm": "$[taskcat_getval_PasswordA]",
            "PasswordB": "$[taskcat_genpass_32S]",
            "RandomNumber": "$[taskcat_random-numbers]",
            "RandomString": "$[taskcat_random-string]",
            "SingleAZ": "$[taskcat_getsingleaz_2]",
            "StackName": "TestStack",
            "UUID": "$[taskcat_genuuid]",
            "BucketRegion": "$[taskcat_current_region]",
        }
        bclient = MockClient
        bclient.logger = logger
        class_kwargs = copy.deepcopy(self.class_kwargs)
        class_kwargs["param_dict"] = input_params
        class_kwargs["boto_client"] = bclient
        pg = ParamGen(**class_kwargs)
        pg.transform_parameter()
        ignore_patterns = ["RE_COUNT"]
        missed_regex_patterns = []
        regex_pattern_text = set()
        _found = False
        for rp in self.regex_patterns:
            regex_pattern_text.add(rp.test_pattern_attribute)
            for _param_key, param_value in pg.results.items():
                if rp.test_pattern_attribute in ignore_patterns:
                    continue
                with self.subTest(
                    "Transformed Value: {} must not match Regex: {}".format(
                        param_value, rp.test_pattern_attribute
                    )
                ):
                    self.assertNotRegex(
                        param_value, getattr(pg, rp.test_pattern_attribute)
                    )
        regex_pattern_text = list(regex_pattern_text)
        for rp in self.regex_patterns:
            regex_test = re.compile(getattr(pg, rp.test_pattern_attribute))
            for _param_key, param_value in input_params.items():
                if regex_test.search(param_value):
                    _found = True
            if not _found:
                missed_regex_patterns.append(rp.test_pattern_attribute)
        self.assertEqual(missed_regex_patterns, [])
        subtests = [
            ("SingleAZ transformed value must be us-east-1b", "SingleAZ", "us-east-1b"),
            (
                "CurrentRegion transformed must be us-east-1",
                "CurrentRegion",
                "us-east-1",
            ),
        ]
        for testdata in subtests:
            with self.subTest(testdata[0]):
                for _param_key, param_value in pg.results.items():
                    if _param_key == testdata[1]:
                        self.assertEqual(param_value, testdata[2])

    def test_list_as_param_value(self):
        input_params = {
            "ExampleList": [
                "$[taskcat_getsingleaz_1]",
                "$[taskcat_getsingleaz_2]",
                "foobar",
            ],
            "ExampleString": "$[taskcat_getsingleaz_1]",
        }
        bclient = MockClient
        bclient.logger = logger
        class_kwargs = copy.deepcopy(self.class_kwargs)
        class_kwargs["param_dict"] = input_params
        class_kwargs["boto_client"] = bclient
        pg = ParamGen(**class_kwargs)
        pg.transform_parameter()
        expected_result = {
            "ExampleList": ["us-east-1a", "us-east-1b", "foobar"],
            "ExampleString": "us-east-1a",
        }
        self.assertEqual(pg.results, expected_result)

    @mock.patch("taskcat._template_params.fetch_ssm_parameter_value")
    def test_ssm_parameter_wrapper(self, m_fetch_ssm):
        m_fetch_ssm.return_value = "blah"
        input_params = {
            "Example": "$[taskcat_ssm_/path/to/my/example/ssm_param/nested_with_underscores]"
        }
        bclient = MockClient
        bclient.logger = logger
        class_kwargs = copy.deepcopy(self.class_kwargs)
        class_kwargs["param_dict"] = input_params
        class_kwargs["boto_client"] = bclient
        pg = ParamGen(**class_kwargs)
        pg._get_ssm_param_value_wrapper(pg.RE_SSM_PARAMETER)
        m_fetch_ssm.assert_called_once_with(
            bclient, "/path/to/my/example/ssm_param/nested_with_underscores"
        )
        self.assertEqual(pg.param_value, "blah")

    def test__get_project_name(self):
        input_params = {"Project_Name": "$[taskcat_project_name]"}
        bclient = MockClient
        bclient.logger = logger
        class_kwargs = copy.deepcopy(self.class_kwargs)
        class_kwargs["param_dict"] = input_params
        class_kwargs["boto_client"] = bclient
        pg = ParamGen(**class_kwargs)
        # pg.transform_parameter()
        expected_result = {"Project_Name": "foobar"}
        self.assertEqual(pg.results, expected_result)

    def test__get_test_name(self):
        input_params = {"Test_Name": "$[taskcat_test_name]"}
        bclient = MockClient
        bclient.logger = logger
        class_kwargs = copy.deepcopy(self.class_kwargs)
        class_kwargs["param_dict"] = input_params
        class_kwargs["boto_client"] = bclient
        pg = ParamGen(**class_kwargs)
        # pg.transform_parameter()
        expected_result = {"Test_Name": "testy_mc_testerson"}
        self.assertEqual(pg.results, expected_result)

    # def test_git_branch_repo(self):
    #     base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
    #     base_path = Path(base_path + "data/git_branch_with_repo").resolve()
    #     input_params = {"Branch": "$[taskcat_git_branch]"}
    #     class_kwargs = copy.deepcopy(self.class_kwargs)
    #     class_kwargs["param_dict"] = input_params
    #     class_kwargs["project_root"] = base_path
    #     pg = ParamGen(**class_kwargs)
    #     # pg.transform_parameter()
    #     expected_result = {"Branch": "master"}
    #     self.assertEqual(pg.results, expected_result)

    def test_git_branch_no_repo(self):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/git_branch_with_no_repo").resolve()
        input_params = {"Branch": "$[taskcat_git_branch]"}
        class_kwargs = copy.deepcopy(self.class_kwargs)
        class_kwargs["param_dict"] = input_params
        class_kwargs["project_root"] = base_path
        with self.assertRaises(TaskCatException):
            ParamGen(**class_kwargs)
            # pg.transform_parameter()
