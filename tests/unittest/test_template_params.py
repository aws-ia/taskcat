import unittest
import re
import mock
import logging
from io import BytesIO
import copy
from collections import namedtuple
from taskcat.template_params import ParamGen
from taskcat.client_factory import ClientFactory
from taskcat.exceptions import TaskCatException
logger = logging.getLogger('taskcat')

def client_factory_instance():
    with mock.patch.object(ClientFactory, '__init__', return_value=None):
        aws_clients = ClientFactory(None)
    aws_clients._credential_sets = {'default': [None, None, None, None]}
    aws_clients.logger = logger
    return aws_clients


class MockClientFactory:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get(self, service, region, **xxrgs):
        if service == 's3':
            return MockS3(**self.kwargs)
        else:
            return MockEC2(**self.kwargs)

class MockS3:
    def  get_object(self, Key, **kwargs):
        objresp = {
            'Body': BytesIO(u'unicorns'.encode('utf-8'))
        }
        return objresp

class MockEC2:
    def __init__(self, **kwargs):
        self.describe_az_output = {
            "AvailabilityZones": [
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1a"
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1b"
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1c"
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1d"
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1e"
                },
                {
                    "State": "available",
                    "Messages": [],
                    "RegionName": "us-east-1",
                    "ZoneName": "us-east-1f"
                }
            ]
        }
        for k,v in kwargs.items():
            if k == 'ec2_single_az' and v:
                self.describe_az_output['AvailabilityZones'] = [self.describe_az_output['AvailabilityZones'][0]]
        pass

    def describe_availability_zones(self, Filters):
        outp = self.describe_az_output
        return outp


class TestParamGen(unittest.TestCase):
    class_kwargs = {
        'param_list': [],
        'bucket_name': 'tcat-tag-skdfklsdfklsjf',
        'region': 'us-east-1',
        'boto_client': client_factory_instance()
    }
    rp_namedtup = namedtuple('RegexTestPattern', 'test_string test_pattern_attribute')
    regex_patterns = [
        rp_namedtup(test_string='$[taskcat_getaz_2]', test_pattern_attribute='RE_GENAZ'),
        rp_namedtup(test_string='$[taskcat_genaz_2]', test_pattern_attribute='RE_GENAZ'),
        rp_namedtup(test_string='$[taskcat_random-numbers]', test_pattern_attribute='RE_GENNUMB'),
        rp_namedtup(test_string='$[taskcat_random-string]', test_pattern_attribute='RE_GENRANDSTR'),
        rp_namedtup(test_string='test-path-$[taskcat_random-numbers]-suffix', test_pattern_attribute='RE_GENNUMB'),
        rp_namedtup(test_string='test-path-$[taskcat_random-string]-suffix', test_pattern_attribute='RE_GENRANDSTR'),
        rp_namedtup(test_string='$[taskcat_autobucket]', test_pattern_attribute='RE_GENAUTOBUCKET'),
        rp_namedtup(test_string='https://s3.amazonaws.com/$[taskcat_autobucket]/myproject/', test_pattern_attribute='RE_GENAUTOBUCKET'),
        rp_namedtup(test_string='$[taskcat_genpass_20]', test_pattern_attribute='RE_GENPW'),
        rp_namedtup(test_string='$[taskcat_genpass_20]', test_pattern_attribute='RE_COUNT'),
        rp_namedtup(test_string='$[taskcat_genpass_20A]', test_pattern_attribute='RE_PWTYPE'),
        rp_namedtup(test_string='$[taskcat_gensingleaz_4]', test_pattern_attribute='RE_GENAZ_SINGLE'),
        rp_namedtup(test_string='$[taskcat_getsingleaz_4]', test_pattern_attribute='RE_GENAZ_SINGLE'),
        rp_namedtup(test_string='$[taskcat_getkeypair]', test_pattern_attribute='RE_QSKEYPAIR'),
        rp_namedtup(test_string='$[taskcat_getlicensebucket]', test_pattern_attribute='RE_QSLICBUCKET'),
        rp_namedtup(test_string='$[taskcat_getmediabucket]', test_pattern_attribute='RE_QSMEDIABUCKET'),
        rp_namedtup(test_string='$[taskcat_getlicensecontent]', test_pattern_attribute='RE_GETLICCONTENT'),
        rp_namedtup(test_string='$[taskcat_presignedurl],bucket,key,100', test_pattern_attribute='RE_GETPRESIGNEDURL'),
        rp_namedtup(test_string='$[taskcat_getval_foo]', test_pattern_attribute='RE_GETVAL'),
        rp_namedtup(test_string='$[taskcat_genuuid]', test_pattern_attribute='RE_GENUUID'),
        rp_namedtup(test_string='$[taskcat_genguid]', test_pattern_attribute='RE_GENUUID'),
        rp_namedtup(test_string='$[taskcat_url_http://example.com]', test_pattern_attribute='RE_GETURL')
    ]

    def test_regxfind(self):
        pg = ParamGen(**self.class_kwargs)
        re_object = re.compile('foo')
        self.assertEqual(pg.regxfind(re_object, 'aslkjfafoo'), 'foo')

    def test_regex_replace_param_value(self):
        return False

    def test_regular_expressions(self):
        for i in self.regex_patterns:
            with self.subTest(i=i):
                self.assertRegex(i.test_string, getattr(ParamGen, i.test_pattern_attribute))

    def test_special_regular_expression(self):
        pg = ParamGen(**self.class_kwargs)
        self.assertEqual(pg.regxfind(ParamGen.RE_COUNT, '$[taskcat_getaz_2]'), '2')
        self.assertEqual(pg.regxfind(ParamGen.RE_COUNT, '$[taskcat_genpass_8]'), '8')

    def test_get_available_azs(self):
        pg = ParamGen(**self.class_kwargs)
        acceptable_azs = ['us-east-1a','us-east-1b','us-east-1c','us-east-1d','us-east-1e','us-east-1f']
        pg._boto_client = MockClientFactory()
        returned_azs = pg.get_available_azs(2)
        returned_az_list = returned_azs.split(',')
        test_criteria = [
            # tuple (first_param, second_param, test_description)
            (len(returned_az_list), 2, "Verifying we return 2 AZs"),
            (len(set(returned_az_list)), 2, "Verifying we return 2 *unique* AZs")
        ]
        for first_param, second_param, test_desc in test_criteria:
            with self.subTest(test_desc):
                self.assertEqual(first_param, second_param)

    def test_genaz_raises_taskcat_exception(self):
        pg = ParamGen(**self.class_kwargs)
        pg._boto_client = MockClientFactory(ec2_single_az=True)
        with self.assertRaises(TaskCatException):
            pg.get_available_azs(2)

    def test_get_content(self):
        pg = ParamGen(**self.class_kwargs)
        pg._boto_client = MockClientFactory()
        self.assertEqual(pg.get_content(bucket='unit-test-bucket', object_key='unit-test-key'), 'unicorns')

    def test_genpassword_type(self):
        pg = ParamGen(**self.class_kwargs)
        genpassword_criteria = [
            # A tuple of (func_call, length, flags, re.Pattern, description)
            (pg.genpassword, 15, None, re.compile('[0-9A-Za-z]'), 'Testing a 15 character password. Default PW type'),
            (pg.genpassword, 15, 'S', re.compile("[!#\$&{\*:\[=,\]-_%@\+a-zA-Z0-9]+"), 'Testing a 15 character password, Special Characters Type'),
            (pg.genpassword, 15, 'A', re.compile('[0-9A-Za-z]'), 'Testing a 15 character password, Alphanumeric Character Type')
        ]
        for func_call, pwlen, pwflags, re_pattern, test_desc in genpassword_criteria:
            with self.subTest(test_desc):
                self.assertRegex(func_call(pwlen, pwflags), re_pattern)

    def test_genpassword_length(self):
        pg = ParamGen(**self.class_kwargs)
        self.assertEqual(len(pg.genpassword(15)), 15)

    def test_gen_rand_str_regex(self):
        genstr = ParamGen._gen_rand_str(24)
        self.assertRegex(genstr, re.compile('[a-z]'))

    def test_gen_rand_str_len(self):
        genstr = ParamGen._gen_rand_str(33)
        self.assertEqual(len(genstr), 33)

    def test_gen_rand_num(self):
        genstr = ParamGen._gen_rand_num(24)
        self.assertRegex(genstr, re.compile('[0-9]'))

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
        self.assertRegex(generated_uuid, re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'))

    def test_all_regexes_tested(self):
        regex_type = type(re.compile(''))
        tested_expressions = set([x.test_pattern_attribute for x in self.regex_patterns])
        all_expressions = set([x for x in dir(ParamGen) if type(getattr(ParamGen, x)) == regex_type])
        self.assertEqual(all_expressions, tested_expressions)

    def test_regex_replace_param_value(self):
        pg = ParamGen(**self.class_kwargs)
        pg.param_name = 'test_param'
        pg.param_value = 'example-foo-value'
        re_pattern = re.compile('foo')
        pg._regex_replace_param_value(re_pattern, 'bar')
        self.assertEqual(pg.param_value, 'example-bar-value')

    def test_convert_to_str(self):
        pg = ParamGen(**self.class_kwargs)
        pg.param_name = 'test_param'
        pg.param_value = 1234
        pg.convert_to_str()
        self.assertEqual(pg.param_value, '1234')

    def test_param_transform(self):
        input_params = [
            {
                "ParameterKey": "AvailabilityZones",
                "ParameterValue": "$[taskcat_genaz_3]"
            },
            {
                "ParameterKey":"SingleAZ",
                "ParameterValue": "$[taskcat_getsingleaz_2]"
            },
            {
                "ParameterKey": "StackName",
                "ParameterValue": "TestStack"
            },
            {
                "ParameterKey": "ByteValue",
                "ParameterValue": '1'
            },
            {
                "ParameterKey": "UUID",
                "ParameterValue": "$[taskcat_genuuid]"
            },
            {
                "ParameterKey": "RandomNumber",
                "ParameterValue": "$[taskcat_random-numbers]"
            },
            {
                "ParameterKey": "RandomString",
                "ParameterValue": "$[taskcat_random-string]"
            },
            {
                "ParameterKey": "UUID",
                "ParameterValue": "$[taskcat_genuuid]"
            },
            {
                "ParameterKey": "PasswordA",
                "ParameterValue": "$[taskcat_genpass_8A]"
            },
            {
                "ParameterKey": "PasswordAConfirm",
                "ParameterValue": "$[taskcat_getval_PasswordA]"
            },
            {
                "ParameterKey": "PasswordB",
                "ParameterValue": "$[taskcat_genpass_32S]"
            },
            {
                "ParameterKey":"LocalOverrideTest",
                "ParameterValue":"override"
            },
            {
                "ParameterKey":"GlobalOverrideTest",
                "ParameterValue":"override"
            }
        ]
        bclient = MockClientFactory()
        bclient.logger = logger
        class_kwargs = self.class_kwargs
        class_kwargs['param_list'] = input_params
        class_kwargs['boto_client'] =  bclient
        pg = ParamGen(**class_kwargs)
        pg.transform_parameter()
        transformed_params = [x['ParameterValue'] for x in pg.results]
        original_params = [x['ParameterValue'] for x in input_params]
        ignore_patterns = ['RE_COUNT']
        missed_regex_patterns = []
        regex_pattern_text = set()
        _found = False
        for rp in self.regex_patterns:
            regex_pattern_text.add(rp.test_pattern_attribute)
            for tp in transformed_params:
                if rp.test_pattern_attribute in ignore_patterns:
                    continue
                with self.subTest("Transformed Value: {} must not match Regex: {}".format(tp, rp.test_pattern_attribute)):
                    self.assertNotRegex(tp, getattr(pg,rp.test_pattern_attribute))
        regex_pattern_text = list(regex_pattern_text)
        for rp in self.regex_patterns:
            regex_test = re.compile(getattr(pg, rp.test_pattern_attribute))
            for tp in original_params:
                if regex_test.search(tp):
                    _found = True
            if not _found:
                missed_regex_patterns.append(rp.test_pattern_attribute)
        self.assertEqual(missed_regex_patterns, [])
        with self.subTest("SingleAZ transformed value must be us-east-1b"):
            for r in pg.results:
                if r['ParameterKey'] == 'SingleAZ':
                    self.assertEqual(r['ParameterValue'], 'us-east-1b')