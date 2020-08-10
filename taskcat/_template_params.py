import logging
import random
import re
import uuid
from typing import Set

from taskcat._common_utils import (
    CommonTools,
    fetch_secretsmanager_parameter_value,
    fetch_ssm_parameter_value,
)
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class ParamGen:
    RE_GETURL = re.compile(r"(?<=._url_)(.+)(?=]$)", re.IGNORECASE)
    RE_COUNT = re.compile(r"(?!\w+_)\d{1,2}", re.IGNORECASE)
    RE_PWTYPE = re.compile(r"(?<=_genpass_)((\d+)(\w)(\]))", re.IGNORECASE)
    RE_GENPW = re.compile(r"\$\[\w+_genpass?(\w)_\d{1,2}\w?]$", re.IGNORECASE)
    RE_GENRANDSTR = re.compile(r"\$\[taskcat_random-string]", re.IGNORECASE)
    RE_GENNUMB = re.compile(r"\$\[taskcat_random-numbers]", re.IGNORECASE)
    RE_GENAUTOBUCKET = re.compile(r"\$\[taskcat_autobucket]", re.IGNORECASE)
    RE_GENAZ = re.compile(r"\$\[\w+_ge[nt]az_\d]", re.IGNORECASE)
    RE_GENAZ_SINGLE = re.compile(
        r"\$\[\w+_ge[nt]singleaz_(?P<az_id>\d+)]", re.IGNORECASE
    )
    RE_GENUUID = re.compile(r"\$\[\w+_gen[gu]uid]", re.IGNORECASE)
    RE_QSKEYPAIR = re.compile(r"\$\[\w+_getkeypair]", re.IGNORECASE)
    RE_QSLICBUCKET = re.compile(r"\$\[\w+_getlicensebucket]", re.IGNORECASE)
    RE_QSMEDIABUCKET = re.compile(r"\$\[\w+_getmediabucket]", re.IGNORECASE)
    RE_GETLICCONTENT = re.compile(r"\$\[\w+_getlicensecontent].*$", re.IGNORECASE)
    RE_GETPRESIGNEDURL = re.compile(
        r"\$\[\w+_presignedurl],(.*?,){1,2}.*?$", re.IGNORECASE
    )
    RE_GETVAL = re.compile(r"(?<=._getval_)(\w+)(?=]$)", re.IGNORECASE)
    RE_CURRENT_REGION = re.compile(r"\$\[taskcat_current_region]", re.IGNORECASE)
    RE_PROJECT_NAME = re.compile(r"\$\[taskcat_project_name]", re.IGNORECASE)
    RE_TEST_NAME = re.compile(r"\$\[taskcat_test_name]", re.IGNORECASE)
    RE_SSM_PARAMETER = re.compile(r"\$\[taskcat_ssm_.*]$", re.IGNORECASE)
    RE_SECRETSMANAGER_PARAMETER = re.compile(
        r"\$\[taskcat_secretsmanager_.*]$", re.IGNORECASE
    )

    def __init__(
        self,
        param_dict,
        bucket_name,
        region,
        boto_client,
        project_name,
        test_name,
        az_excludes=None,
    ):
        self.regxfind = CommonTools.regxfind
        self._param_dict = param_dict
        _missing_params = []
        for param_name, param_value in param_dict.items():
            if param_value is None:
                _missing_params.append(param_name)
        if _missing_params:
            raise TaskCatException(
                (
                    f"The following parameters have no value whatsoever. "
                    f"The CloudFormation stack will fail to launch. "
                    f"Please address. str({_missing_params})"
                )
            )
        self.results = {}
        self.mutated_params = {}
        self.param_name = None
        self.param_value = None
        self.bucket_name = bucket_name
        self._boto_client = boto_client
        self.region = region
        self.project_name = project_name
        self.test_name = test_name
        if not az_excludes:
            self.az_excludes: Set[str] = set()
        else:
            self.az_excludes: Set[str] = az_excludes
        self.transform_parameter()

    def transform_parameter(self):
        # Depreciated placeholders:
        # - $[taskcat_gets3contents]
        # - $[taskcat_geturl]
        for param_name, param_value in self._param_dict.items():
            if isinstance(param_value, list):
                _results_list = []
                _nested_param_dict = {}
                for idx, value in enumerate(param_value):
                    _nested_param_dict[idx] = value
                nested_pg = ParamGen(
                    _nested_param_dict,
                    self.bucket_name,
                    self.region,
                    self._boto_client,
                    self.project_name,
                    self.test_name,
                    self.az_excludes,
                )
                nested_pg.transform_parameter()
                for result_value in nested_pg.results.values():
                    _results_list.append(result_value)
                self.param_value = _results_list
                self.results.update({param_name: _results_list})
                continue

            # Setting the instance variables to reflect key/value pair we're working on.
            self.param_name = param_name
            self.param_value = param_value

            # Convert from bytes to string.
            self.convert_to_str()

            # $[taskcat_random-numbers]
            self._regex_replace_param_value(self.RE_GENNUMB, self._gen_rand_num(20))

            # $[taskcat_random-string]
            self._regex_replace_param_value(self.RE_GENRANDSTR, self._gen_rand_str(20))

            # $[taskcat_autobucket]
            self._regex_replace_param_value(
                self.RE_GENAUTOBUCKET, self._gen_autobucket()
            )

            # $[taskcat_genpass_X]
            self._gen_password_wrapper(self.RE_GENPW, self.RE_PWTYPE, self.RE_COUNT)

            # $[taskcat_ge[nt]az_#]
            self._gen_az_wrapper(self.RE_GENAZ, self.RE_COUNT)

            # $[taskcat_ge[nt]singleaz_#]
            self._gen_single_az_wrapper(self.RE_GENAZ_SINGLE)

            # $[taskcat_getkeypair]
            self._regex_replace_param_value(self.RE_QSKEYPAIR, "cikey")

            # $[taskcat_getlicensebucket]
            self._regex_replace_param_value(self.RE_QSLICBUCKET, "override_this")

            # $[taskcat_getmediabucket]
            self._regex_replace_param_value(self.RE_QSMEDIABUCKET, "override_this")

            # $[taskcat_getlicensecontent]
            self._get_license_content_wrapper(self.RE_GETLICCONTENT)

            # $[taskcat_getpresignedurl]
            self._get_license_content_wrapper(self.RE_GETPRESIGNEDURL)

            # $[taskcat_getval_X]
            self._getval_wrapper(self.RE_GETVAL)

            # $[taskcat_genuuid]
            self._regex_replace_param_value(self.RE_GENUUID, self._gen_uuid())

            # $[taskcat_ssm_X]
            self._get_ssm_param_value_wrapper(self.RE_SSM_PARAMETER)
            # $[taskcat_current_region]
            self._regex_replace_param_value(
                self.RE_CURRENT_REGION, self._gen_current_region()
            )
            self._regex_replace_param_value(
                self.RE_PROJECT_NAME, self._get_project_name()
            )
            self._regex_replace_param_value(self.RE_TEST_NAME, self._get_test_name())
            self.results.update({self.param_name: self.param_value})

    def get_available_azs(self, count):
        """
        Returns a list of availability zones in a given region.

        :param count: Minimum number of availability zones needed

        :return: List of availability zones in a given region

        """
        ec2_client = self._boto_client("ec2")
        available_azs = []
        availability_zones = ec2_client.describe_availability_zones(
            Filters=[{"Name": "state", "Values": ["available"]}]
        )

        for az in availability_zones[  # pylint: disable=invalid-name
            "AvailabilityZones"
        ]:
            if az["ZoneId"] in self.az_excludes:
                continue
            available_azs.append(az["ZoneName"])

        if len(available_azs) < count:
            raise TaskCatException(
                "!Only {0} az's are available in {1}".format(
                    len(available_azs), self.region
                )
            )
        azs = ",".join(available_azs[:count])
        return azs

    def get_single_az(self, az_id):
        """
        Get a single valid AZ for the region.
        The number passed indicates the ordinal representing the AZ returned.
        For instance, in the 'us-east-1' region, providing '1' as the ID would
        return 'us-east-1a', providing '2' would return 'us-east-1b', etc.
        In this way it's possible to get availability zones that are
        guaranteed to be different without knowing their names.
        :param az_id: 0-based ordinal of the AZ to get
        :return: The requested availability zone of the specified region.
        """

        regional_azs = self.get_available_azs(az_id)
        return regional_azs.split(",")[-1]

    def get_content(self, bucket, object_key):
        """
        Returns the content of an object, given the bucket name and the key of the
        object

        :param bucket: Bucket name
        :param object_key: Key of the object
        :param object_key: Key of the object
        :return: Content of the object

        """
        s3_client = self._boto_client("s3")
        try:
            dict_object = s3_client.get_object(Bucket=bucket, Key=object_key)
        except Exception:
            LOG.error(
                "Attempted to fetch Bucket: {}, Key: {}".format(bucket, object_key)
            )
            raise
        content = dict_object["Body"].read().decode("utf-8").strip()
        return content

    @staticmethod
    def genpassword(pass_length, pass_type=None):
        """
        Returns a password of given length and type.

        :param pass_length: Length of the desired password
        :param pass_type: Type of the desired password - String only OR Alphanumeric
            * A = AlphaNumeric, Example 'vGceIP8EHC'
        :return: Password of given length and type
        """

        password = []
        numbers = "1234567890"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        specialchars = "!#$&{*:[=,]-_%@+"

        # Generates password string with:
        # lowercase,uppercase and numeric chars
        if pass_type == "A":  # nosec

            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        # Generates password string with:
        # lowercase,uppercase, numbers and special chars
        elif pass_type == "S":
            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))
                password.append(random.choice(specialchars))
        else:
            # If no passtype is defined (None)
            # Defaults to alpha-numeric
            # Generates password string with:
            # lowercase,uppercase, numbers and special chars
            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        if len(password) > pass_length:
            password = password[:pass_length]

        return "".join(password)

    def convert_to_str(self):
        """
        Converts a parameter value to string
        No parameters. Operates on (ClassInstance).param_value
        """
        if isinstance(self.param_value, (int, float, bytes)):
            self.param_value = str(self.param_value)

    @staticmethod
    def _gen_rand_str(length):
        random_string_list = []
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        while len(random_string_list) < length:
            random_string_list.append(random.choice(lowercase))  # nosec
        return "".join(random_string_list)

    @staticmethod
    def _gen_rand_num(length):
        random_number_list = []
        numbers = "1234567890"
        while len(random_number_list) < length:
            random_number_list.append(random.choice(numbers))  # nosec
        return "".join(random_number_list)

    @staticmethod
    def _gen_uuid():
        return str(uuid.uuid1())

    def _gen_autobucket(self):
        return self.bucket_name

    def _gen_current_region(self):
        return self.region

    def _get_project_name(self):
        return self.project_name

    def _get_test_name(self):
        return self.test_name

    def _gen_password_wrapper(self, gen_regex, type_regex, count_regex):
        if gen_regex.search(self.param_value):
            passlen = int(self.regxfind(count_regex, self.param_value))
            gentype = self.regxfind(type_regex, self.param_value)
            # Additional computation to identify if the gentype is one of the desired
            # values. Sample gentype values would be '8A]' or '24S]' or '2]' To get
            # the correct gentype, get 2nd char from the last and check if its A or S
            gentype = gentype[-2]
            if gentype in ("a", "A", "s", "S"):
                gentype = gentype.upper()
            else:
                gentype = None
            if not gentype:
                # Set default password type
                # A value of PrintMsg.DEBUG will generate a simple alpha
                # aplha numeric password
                gentype = "D"

            if passlen:
                param_value = self.genpassword(passlen, gentype)
                self._regex_replace_param_value(gen_regex, param_value)

    def _gen_az_wrapper(self, genaz_regex, count_regex):
        if genaz_regex.search(self.param_value):
            numazs = int(self.regxfind(count_regex, self.param_value))
            if numazs:

                self._regex_replace_param_value(
                    genaz_regex, self.get_available_azs(numazs)
                )

            else:
                LOG.info("$[taskcat_genaz_(!)]")
                LOG.info("Number of az's not specified!")
                LOG.info(" - (Defaulting to 1 az)")
                self._regex_replace_param_value(genaz_regex, self.get_available_azs(1))

    def _gen_single_az_wrapper(self, genaz_regex):
        if genaz_regex.search(self.param_value):
            az_id = int(genaz_regex.search(self.param_value).group("az_id"))
            self._regex_replace_param_value(genaz_regex, self.get_single_az(az_id))

    def _get_license_content_wrapper(self, license_content_regex):
        if license_content_regex.search(self.param_value):
            license_str = self.regxfind(license_content_regex, self.param_value)
            license_bucket = license_str.split("/")[1]
            licensekey = "/".join(license_str.split("/")[2:])
            param_value = self.get_content(license_bucket, licensekey)
            self._regex_replace_param_value(re.compile("^.*$"), param_value)

    def _get_presigned_url_wrapper(self, presigned_url_regex):
        if presigned_url_regex.search(self.param_value):
            if len(self.param_value) < 2:
                LOG.error("Syntax: $[taskcat_presignedurl],bucket,key,OPTIONAL_TIMEOUT")
                raise TaskCatException(
                    "Syntax error when using $[taskcat_getpresignedurl]; Not "
                    "enough parameters."
                )
            paramsplit = self.regxfind(presigned_url_regex, self.param_value).split(
                ","
            )[1:]
            url_bucket, url_key = paramsplit[:2]
            if len(paramsplit) == 3:
                url_expire_seconds = paramsplit[2]
            else:
                url_expire_seconds = 3600
            s3_client = self._boto_client("s3")
            param_value = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": url_bucket, "Key": url_key},
                ExpiresIn=int(url_expire_seconds),
            )
            self._regex_replace_param_value(re.compile("^.*$"), param_value)
            self._regex_replace_param_value(re.compile("^.*$"), param_value)

    def _get_ssm_param_value_wrapper(self, ssm_param_value_regex):
        if ssm_param_value_regex.search(self.param_value):
            ssm_value_str = self.regxfind(ssm_param_value_regex, self.param_value)
            param_path = "_".join(ssm_value_str[:-1].split("_")[2:])
            param_value = fetch_ssm_parameter_value(self._boto_client, param_path)
            self._regex_replace_param_value(re.compile("^.*"), param_value)

    def _get_secretsmanager_param_value_wrapper(self, secretsmanager_param_value_regex):
        if secretsmanager_param_value_regex.search(self.param_value):
            sm_value_str = self.regxfind(
                secretsmanager_param_value_regex, self.param_value
            )
            sm_arn = "_".join(sm_value_str.split("_")[2:])
            param_value = fetch_secretsmanager_parameter_value(
                self._boto_client, sm_arn
            )
            self._regex_replace_param_value(re.compile("^.*"), param_value)

    def _getval_wrapper(self, getval_regex):
        if getval_regex.search(self.param_value):
            requested_key = self.regxfind(getval_regex, self.param_value)
            self._regex_replace_param_value(
                re.compile("^.*$"), self.mutated_params[requested_key]
            )

    def _regex_replace_param_value(self, regex_pattern, func_output):
        if self.regxfind(regex_pattern, self.param_value):
            self.param_value = re.sub(regex_pattern, str(func_output), self.param_value)
            self.mutated_params[self.param_name] = self.param_value
