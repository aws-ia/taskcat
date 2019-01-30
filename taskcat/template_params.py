import re
import random
import uuid
import logging
from taskcat.colored_console import PrintMsg
from taskcat.exceptions import TaskCatException

logger = logging.getLogger('taskcat')
class ParamGen:

    RE_GETURL = re.compile(
        '(?<=._url_)(.+)(?=]$)', re.IGNORECASE)
    RE_COUNT = re.compile(
        '(?!\w+_)\d{1,2}', re.IGNORECASE)
    RE_PWTYPE = re.compile(
        '(?<=_genpass_)((\d+)(\w)(\]))', re.IGNORECASE)
    RE_GENPW = re.compile(
        '\$\[\w+_genpass?(\w)_\d{1,2}\w?]$', re.IGNORECASE)
    RE_GENRANDSTR = re.compile(
        '\$\[taskcat_random-string]', re.IGNORECASE)
    RE_GENNUMB = re.compile(
        '\$\[taskcat_random-numbers]', re.IGNORECASE)
    RE_GENAUTOBUCKET = re.compile(
        '\$\[taskcat_autobucket]', re.IGNORECASE)
    RE_GENAZ = re.compile('\$\[\w+_ge[nt]az_\d]', re.IGNORECASE)
    RE_GENAZ_SINGLE = re.compile('\$\[\w+_ge[nt]singleaz_(?P<az_id>\d+)]', re.IGNORECASE)
    RE_GENUUID = re.compile('\$\[\w+_gen[gu]uid]', re.IGNORECASE)
    RE_QSKEYPAIR = re.compile('\$\[\w+_getkeypair]', re.IGNORECASE)
    RE_QSLICBUCKET = re.compile('\$\[\w+_getlicensebucket]', re.IGNORECASE)
    RE_QSMEDIABUCKET = re.compile('\$\[\w+_getmediabucket]', re.IGNORECASE)
    RE_GETLICCONTENT = re.compile('\$\[\w+_getlicensecontent].*$', re.IGNORECASE)
    RE_GETPRESIGNEDURL = re.compile('\$\[\w+_presignedurl],(.*?,){1,2}.*?$', re.IGNORECASE)
    RE_GETVAL = re.compile('(?<=._getval_)(\w+)(?=]$)', re.IGNORECASE)

    def __init__(self, param_list, bucket_name, region, boto_client, verbose=False):
        self._param_list = param_list
        self.results = []
        self.mutated_params = {}
        self.param_name = None
        self.param_value = None
        self.verbose = verbose
        self.bucket_name = bucket_name
        self._boto_client = boto_client
        self.region = region
        self.transform_parameter()

    def transform_parameter(self):
        # Depreciated placeholders:
        # - $[taskcat_gets3contents]
        # - $[taskcat_geturl]
        for p in self._param_list:
            # Setting the instance variables to reflect key/value pair we're working on.
            self.param_name = p['ParameterKey']
            self.param_value = p['ParameterValue']

            # Convert from bytes to string.
            self.convert_to_str()

            # $[taskcat_random-numbers]
            self._regex_replace_param_value(self.RE_GENNUMB, self._gen_rand_num(20))

            # $[taskcat_random-string]
            self._regex_replace_param_value(self.RE_GENRANDSTR, self._gen_rand_str(20))

            # $[taskcat_autobucket]
            self._regex_replace_param_value(self.RE_GENAUTOBUCKET, self._gen_autobucket())

            # $[taskcat_genpass_X]
            self._gen_password_wrapper(self.RE_GENPW, self.RE_PWTYPE, self.RE_COUNT)

            # $[taskcat_ge[nt]az_#]
            self._gen_az_wrapper(self.RE_GENAZ, self.RE_COUNT)

            # $[taskcat_ge[nt]singleaz_#]
            self._gen_single_az_wrapper(self.RE_GENAZ_SINGLE)

            # $[taskcat_getkeypair]
            self._regex_replace_param_value(self.RE_QSKEYPAIR, 'cikey')

            # $[taskcat_getlicensebucket]
            self._regex_replace_param_value(self.RE_QSLICBUCKET, 'override_this')

            # $[taskcat_getmediabucket]
            self._regex_replace_param_value(self.RE_QSMEDIABUCKET, 'override_this')

            # $[taskcat_getlicensecontent]
            self._get_license_content_wrapper(self.RE_GETLICCONTENT)

            # $[taskcat_getpresignedurl]
            self._get_license_content_wrapper(self.RE_GETPRESIGNEDURL)

            # $[taskcat_getval_X]
            self._getval_wrapper(self.RE_GETVAL)

            # $[taskcat_genuuid]
            self._regex_replace_param_value(self.RE_GENUUID, self._gen_uuid())

            self.results.append({'ParameterKey': self.param_name, 'ParameterValue': self.param_value})


    @staticmethod
    def regxfind(re_object, data_line):
        """
        Returns the matching string.

        :param re_object: Regex object
        :param data_line: String to be searched

        :return: Matching String if found, otherwise return 'Not-found'
        """
        sg = re_object.search(data_line)
        if sg:
            return str(sg.group())
        else:
            return str('Not-found')

    def get_available_azs(self, count):
        """
        Returns a list of availability zones in a given region.

        :param region: Region for the availability zones
        :param count: Minimum number of availability zones needed

        :return: List of availability zones in a given region

        """
        ec2_client = self._boto_client.get('ec2', region=self.region)
        available_azs = []
        availability_zones = ec2_client.describe_availability_zones(
            Filters=[{'Name': 'state', 'Values': ['available']}])

        for az in availability_zones['AvailabilityZones']:
            available_azs.append(az['ZoneName'])

        if len(available_azs) < count:
            print("{0}!Only {1} az's are available in {2}".format(PrintMsg.ERROR, len(available_azs), self.region))
            raise TaskCatException
        else:
            azs = ','.join(available_azs[:count])
            return azs

    def get_single_az(self, az_id):
        """
        Get a single valid AZ for the region.
        The number passed indicates the ordinal representing the AZ returned.
        For instance, in the 'us-east-1' region, providing '1' as the ID would
        return 'us-east-1a', providing '2' would return 'us-east-1b', etc.
        In this way it's possible to get availability zones that are
        guaranteed to be different without knowing their names.
        :param region: Region of the availability zone
        :param az_id: 0-based ordinal of the AZ to get
        :return: The requested availability zone of the specified region.
        """

        regional_azs = self.get_available_azs(az_id)
        return regional_azs.split(',')[-1]

    def get_content(self, bucket, object_key):
        """
        Returns the content of an object, given the bucket name and the key of the object

        :param bucket: Bucket name
        :param object_key: Key of the object
        :param object_key: Key of the object
        :return: Content of the object

        """
        s3_client = self._boto_client.get('s3', region=self.region, s3v4=True)
        try:
            dict_object = s3_client.get_object(Bucket=bucket, Key=object_key)
        except TaskCatException:
            raise
        except Exception:
            print("{} Attempted to fetch Bucket: {}, Key: {}".format(PrintMsg.ERROR, bucket, object_key))
            raise
        content = dict_object['Body'].read().decode('utf-8').strip()
        return content

    def genpassword(self, pass_length, pass_type=None):
        """
        Returns a password of given length and type.

        :param pass_length: Length of the desired password
        :param pass_type: Type of the desired password - String only OR Alphanumeric
            * A = AlphaNumeric, Example 'vGceIP8EHC'
        :return: Password of given length and type
        """
        if self.verbose:
            print(PrintMsg.DEBUG + "Auto generating password")
            print(PrintMsg.DEBUG + "Pass size => {0}".format(pass_length))

        password = []
        numbers = "1234567890"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        specialchars = "!#$&{*:[=,]-_%@+"

        # Generates password string with:
        # lowercase,uppercase and numeric chars
        if pass_type == 'A':
            print(PrintMsg.DEBUG + "Pass type => {0}".format('alpha-numeric'))

            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        # Generates password string with:
        # lowercase,uppercase, numbers and special chars
        elif pass_type == 'S':
            print(PrintMsg.DEBUG + "Pass type => {0}".format('specialchars'))
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
            print(PrintMsg.DEBUG + "Pass type => default {0}".format('alpha-numeric'))
            while len(password) < pass_length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        if len(password) > pass_length:
            password = password[:pass_length]

        return ''.join(password)

    def convert_to_str(self):
        """
        Converts a parameter value to string
        No parameters. Operates on (ClassInstance).param_value
        """
        if (type(self.param_value) == int) or (type(self.param_value) == bytes):
            if self.verbose:
                print(PrintMsg.INFO + "Converting Parameter {} from integer/bytes to string".format(self.param_name))
            self.param_value = str(self.param_value)

    @staticmethod
    def _gen_rand_str(length):
        random_string_list = []
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        print(PrintMsg.DEBUG + "Generating a {}-character random string".format(length))
        while len(random_string_list) < length:
            random_string_list.append(random.choice(lowercase))
        return ''.join(random_string_list)

    @staticmethod
    def _gen_rand_num(length):
        random_number_list = []
        numbers = "1234567890"
        print(PrintMsg.DEBUG + "Generating a {}-character random string of numbers".format(length))
        while len(random_number_list) < length:
            random_number_list.append(random.choice(numbers))
        return ''.join(random_number_list)

    def _gen_uuid(self):
        return str(uuid.uuid1())

    def _gen_autobucket(self):
        return self.bucket_name

    def _gen_password_wrapper(self, gen_regex, type_regex, count_regex):
        if gen_regex.search(self.param_value):
            passlen = int(
                self.regxfind(count_regex, self.param_value))
            gentype = self.regxfind(
                type_regex, self.param_value)
            # Additional computation to identify if the gentype is one of the desired values.
            # Sample gentype values would be '8A]' or '24S]' or '2]'
            # To get the correct gentype, get 2nd char from the last and check if its A or S
            gentype = gentype[-2]
            if gentype in ('a', 'A', 's', 'S'):
                gentype = gentype.upper()
            else:
                gentype = None
            if not gentype:
                # Set default password type
                # A value of PrintMsg.DEBUG will generate a simple alpha
                # aplha numeric password
                gentype = 'D'

            if passlen:
                if self.verbose:
                    print("{}AutoGen values for {}".format(PrintMsg.DEBUG, self.param_value))
                param_value = self.genpassword(
                    passlen, gentype)
                self._regex_replace_param_value(gen_regex, param_value)

    def _gen_az_wrapper(self, genaz_regex, count_regex):
        if genaz_regex.search(self.param_value):
            numazs = int(
                self.regxfind(count_regex, self.param_value))
            if numazs:
                if self.verbose:
                    print(PrintMsg.DEBUG + "Selecting availability zones")
                    print(PrintMsg.DEBUG + "Requested %s az's" % numazs)

                self._regex_replace_param_value(genaz_regex, self.get_available_azs(numazs))

            else:
                print(PrintMsg.INFO + "$[taskcat_genaz_(!)]")
                print(PrintMsg.INFO + "Number of az's not specified!")
                print(PrintMsg.INFO + " - (Defaulting to 1 az)")
                self._regex_replace_param_value(genaz_regex, self.get_available_azs(1))

    def _gen_single_az_wrapper(self, genaz_regex):
        if genaz_regex.search(self.param_value):
            print(PrintMsg.DEBUG + "Selecting availability zones")
            print(PrintMsg.DEBUG + "Requested 1 az")
            az_id = int(genaz_regex.search(self.param_value).group('az_id'))
            self._regex_replace_param_value(
                genaz_regex, self.get_single_az(az_id))

    def _get_license_content_wrapper(self, license_content_regex):
        if license_content_regex.search(self.param_value):
            license_str = self.regxfind(license_content_regex, self.param_value)
            license_bucket = license_str.split('/')[1]
            licensekey = '/'.join(license_str.split('/')[2:])
            param_value = self.get_content(license_bucket, licensekey)
            if self.verbose:
                print("{}Getting license content for {}/{}".format(PrintMsg.DEBUG, license_bucket, licensekey))
            self._regex_replace_param_value(re.compile('^.*$'), param_value)

    def _get_presigned_url_wrapper(self, presigned_url_regex):
        if presigned_url_regex.search(self.param_value):
            if len(self.param_value) < 2:
                print(PrintMsg.ERROR + "Syntax error when using $[taskcat_getpresignedurl]; Not enough parameters.")
                print(PrintMsg.ERROR+ "Syntax: $[taskcat_presignedurl],bucket,key,OPTIONAL_TIMEOUT")
                raise TaskCatException
            paramsplit = self.regxfind(presigned_url_regex, self.param_value).split(',')[1:]
            url_bucket, url_key = paramsplit[:2]
            if len(paramsplit) == 3:
                url_expire_seconds = paramsplit[2]
            else:
                url_expire_seconds = 3600
            if self.verbose:
                print("{}Generating a presigned URL for {}/{} with a {} second timeout".format(PrintMsg.DEBUG,
                    url_bucket, url_key, url_expire_seconds))
            s3_client = self._boto_client.get('s3', region=self.get_default_region(), s3v4=True)
            param_value = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': url_bucket, 'Key': url_key},
                ExpiresIn=int(url_expire_seconds))
            self._regex_replace_param_value(re.compile('^.*$'), param_value)
            self._regex_replace_param_value(re.compile('^.*$'), param_value)

    def _getval_wrapper(self, getval_regex):
        if getval_regex.search(self.param_value):
            requested_key = self.regxfind(getval_regex, self.param_value)
            print(PrintMsg.DEBUG + "Getting previously assigned value for " + requested_key)
            self._regex_replace_param_value(re.compile('^.*$'), self.mutated_params[requested_key])

    def _regex_replace_param_value(self, regex_pattern, func_output):
        if self.regxfind(regex_pattern, self.param_value):
            self.param_value = re.sub(regex_pattern, str(func_output), self.param_value)
            self.mutated_params[self.param_name] = self.param_value
