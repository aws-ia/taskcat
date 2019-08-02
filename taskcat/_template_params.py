import logging
import random
import re
import uuid

from taskcat._common_utils import CommonTools
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


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

    def __init__(self, param_list, bucket_name, region, boto_client):
        self.regxfind = CommonTools.regxfind
        self._param_list = param_list
        self.results = []
        self.mutated_params = {}
        self.param_name = None
        self.param_value = None
        self.bucket_name = bucket_name
        self._boto_client = boto_client
        self.region = region
        self.transform_parameter()

    def transform_parameter(self):
        # Depreciated placeholders:
        # - $[taskcat_gets3contents]
        # - $[taskcat_geturl]
        for param in self._param_list:
            # Setting the instance variables to reflect key/value pair we're working on.
            self.param_name = param["ParameterKey"]
            self.param_value = param["ParameterValue"]

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

            self.results.append(
                {"ParameterKey": self.param_name, "ParameterValue": self.param_value}
            )

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
            available_azs.append(az["ZoneName"])

        if len(available_azs) < count:
            LOG.error(
                "!Only {0} az's are available in {1}".format(
                    len(available_azs), self.region
                )
            )
            raise TaskCatException
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
        except TaskCatException:
            raise
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
        LOG.debug("Auto generating password")
        LOG.debug("Pass size => {0}".format(pass_length))

        password = []
        numbers = "1234567890"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        specialchars = "!#$&{*:[=,]-_%@+"

        # Generates password string with:
        # lowercase,uppercase and numeric chars
        if pass_type == "A":  # nosec
            LOG.debug("Pass type => {0}".format("alpha-numeric"))

            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        # Generates password string with:
        # lowercase,uppercase, numbers and special chars
        elif pass_type == "S":
            LOG.debug("Pass type => {0}".format("specialchars"))
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
            LOG.debug("Pass type => default {0}".format("alpha-numeric"))
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
        if isinstance(self.param_value, (int, bytes)):
            LOG.debug(
                "Converting Parameter {} from integer/bytes to string".format(
                    self.param_name
                )
            )
            self.param_value = str(self.param_value)

    @staticmethod
    def _gen_rand_str(length):
        random_string_list = []
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        LOG.debug("Generating a {}-character random string".format(length))
        while len(random_string_list) < length:
            random_string_list.append(random.choice(lowercase))  # nosec
        return "".join(random_string_list)

    @staticmethod
    def _gen_rand_num(length):
        random_number_list = []
        numbers = "1234567890"
        LOG.debug("Generating a {}-character random string of numbers".format(length))
        while len(random_number_list) < length:
            random_number_list.append(random.choice(numbers))  # nosec
        return "".join(random_number_list)

    @staticmethod
    def _gen_uuid():
        return str(uuid.uuid1())

    def _gen_autobucket(self):
        return self.bucket_name

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
                LOG.debug("AutoGen values for {}".format(self.param_value))
                param_value = self.genpassword(passlen, gentype)
                self._regex_replace_param_value(gen_regex, param_value)

    def _gen_az_wrapper(self, genaz_regex, count_regex):
        if genaz_regex.search(self.param_value):
            numazs = int(self.regxfind(count_regex, self.param_value))
            if numazs:
                LOG.debug("Selecting availability zones")
                LOG.debug("Requested %s az's" % numazs)

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
            LOG.debug("Selecting availability zones")
            LOG.debug("Requested 1 az")
            az_id = int(genaz_regex.search(self.param_value).group("az_id"))
            self._regex_replace_param_value(genaz_regex, self.get_single_az(az_id))

    def _get_license_content_wrapper(self, license_content_regex):
        if license_content_regex.search(self.param_value):
            license_str = self.regxfind(license_content_regex, self.param_value)
            license_bucket = license_str.split("/")[1]
            licensekey = "/".join(license_str.split("/")[2:])
            param_value = self.get_content(license_bucket, licensekey)
            LOG.debug(
                "Getting license content for {}/{}".format(license_bucket, licensekey)
            )
            self._regex_replace_param_value(re.compile("^.*$"), param_value)

    def _get_presigned_url_wrapper(self, presigned_url_regex):
        if presigned_url_regex.search(self.param_value):
            if len(self.param_value) < 2:
                LOG.error(
                    "Syntax error when using $[taskcat_getpresignedurl]; Not "
                    "enough parameters."
                )
                LOG.error("Syntax: $[taskcat_presignedurl],bucket,key,OPTIONAL_TIMEOUT")
                raise TaskCatException
            paramsplit = self.regxfind(presigned_url_regex, self.param_value).split(
                ","
            )[1:]
            url_bucket, url_key = paramsplit[:2]
            if len(paramsplit) == 3:
                url_expire_seconds = paramsplit[2]
            else:
                url_expire_seconds = 3600
            LOG.debug(
                "Generating a presigned URL for {}/{} with a {} second timeout".format(
                    url_bucket, url_key, url_expire_seconds
                )
            )
            s3_client = self._boto_client("s3")
            param_value = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": url_bucket, "Key": url_key},
                ExpiresIn=int(url_expire_seconds),
            )
            self._regex_replace_param_value(re.compile("^.*$"), param_value)
            self._regex_replace_param_value(re.compile("^.*$"), param_value)

    def _getval_wrapper(self, getval_regex):
        if getval_regex.search(self.param_value):
            requested_key = self.regxfind(getval_regex, self.param_value)
            LOG.debug("Getting previously assigned value for " + requested_key)
            self._regex_replace_param_value(
                re.compile("^.*$"), self.mutated_params[requested_key]
            )

    def _regex_replace_param_value(self, regex_pattern, func_output):
        if self.regxfind(regex_pattern, self.param_value):
            self.param_value = re.sub(regex_pattern, str(func_output), self.param_value)
            self.mutated_params[self.param_name] = self.param_value
