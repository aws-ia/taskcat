import random
import uuid

from .utils import ClientFactory
from .password_generator import PasswordGenerator
from .formatter import DEBUG, INFO, ERROR
from .input_parameter_regex import (password_size_re,
                                    password_type_re,
                                    generate_password_requested_re,
                                    generate_random_string_requested_re,
                                    generate_random_number_requested_re,
                                    autobucket_requested_re,
                                    generate_az_requested_re,
                                    generate_single_az_requested_re,
                                    generate_uuid_requested_re,
                                    default_keypair_requested_re,
                                    default_license_bucket_requested_re,
                                    default_media_bucket_requested_re,
                                    license_content_requested_re,
                                    presigned_url_requested_re,
                                    s3_replacement_requested_re,
                                    get_url_re,
                                    get_val_requested_re)


class InputParameterGenerator:
    def __init__(self,
                 aws_client_factory=ClientFactory(),
                 password_generator=PasswordGenerator(),
                 parameter_file=None,
                 verbose=False):
        self.aws_client_factory = aws_client_factory
        self.password_generator = password_generator
        self.parameter_file = parameter_file
        self.verbose = verbose
        self.parameters = {}

    def set_parameter(self, key, value):
        self.parameters[key] = value

    def get_parameter(self, key):
        return self.parameters[key]

    def regxfind(self, re_object, data_line):
        """
        Returns the matching string.

        :param re_object: Regex object
        :param data_line: String to be searched

        :return: Matching String if found, otherwise return 'Not-found'
        """
        sg = re_object.search(data_line)
        if sg:
            return str(sg.group())
        return str('Not-found')

    def get_available_azs(self, region, count):
        """
        Returns a list of availability zones in a given region.

        :param region: Region for the availability zones
        :param count: Minimum number of availability zones needed

        :return: List of availability zones in a given region

        """
        available_azs = []
        ec2_client = self.aws_client_factory.get('ec2', region=region)
        availability_zones = ec2_client.describe_availability_zones(
            Filters=[{'Name': 'state', 'Values': ['available']}])

        for az in availability_zones['AvailabilityZones']:
            available_azs.append(az['ZoneName'])

        if len(available_azs) < count:
            print("{0}!Only {1} az's are available in {2}".format(ERROR, len(available_azs), region))
            quit(1)
        else:
            azs = ','.join(available_azs[:count])
            return azs

    def generate_uuid(self, uuid_type):
        if uuid_type is 'A':
            return str(uuid.uuid4())
        else:
            return str(uuid.uuid4())

    def _wrap_raw_values(self, value):
        if type(value) == int:
            value = str(value)
            if self.verbose:
                print(INFO + "Converting byte values in stack input file({}) to [string value]".format(self.parameter_file))
        return value

    def generate_random(self, gtype, length):
        random_string = []
        numbers = "1234567890"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        if gtype == 'alpha':
            print(DEBUG + "Random String => {0}".format('alpha'))

            while len(random_string) < length:
                random_string.append(random.choice(lowercase))

        # Generates password string with:
        # lowercase,uppercase, numbers and special chars
        elif gtype == 'number':
            print(DEBUG + "Random String => {0}".format('numeric'))
            while len(random_string) < length:
                random_string.append(random.choice(numbers))

        return ''.join(random_string)

    def generate_password(self, password_length, password_type):
        return self.password_generator.generate(password_length, password_type)

    def generate(self, input_parameters, region):
        for _parameters in input_parameters:
            for _ in _parameters:
                param_key = _parameters['ParameterKey']
                param_value = _parameters['ParameterValue']
                # If Number is found as Parameter Value convert it to String ( ex: 1 to "1")
                param_value = self._wrap_raw_values(param_value)
                _parameters['ParameterValue'] = param_value
                self.set_parameter(param_key, param_value)

                if generate_random_string_requested_re.search(param_value):
                    random_string = self.regxfind(generate_random_string_requested_re, param_value)
                    param_value = self.generate_random('alpha', 20)

                    if self.verbose:
                        print("{}Generating random string for {}".format(DEBUG, random_string))
                    _parameters['ParameterValue'] = param_value

                if generate_random_number_requested_re.search(param_value):
                    random_numbers = self.regxfind(generate_random_number_requested_re, param_value)
                    param_value = self.generate_random('number', 20)

                    if self.verbose:
                        print("{}Generating numeric string for {}".format(DEBUG, random_numbers))
                    _parameters['ParameterValue'] = param_value

                if generate_uuid_requested_re.search(param_value):
                    uuid_string = self.regxfind(generate_uuid_requested_re, param_value)
                    param_value = self.generate_uuid('A')

                    if self.verbose:
                        print("{}Generating random uuid string for {}".format(DEBUG, uuid_string))
                    _parameters['ParameterValue'] = param_value

                if autobucket_requested_re.search(param_value):
                    bkt = self.regxfind(autobucket_requested_re, param_value)
                    param_value = self.get_s3bucket()
                    if self.verbose:
                        print("{}Setting value to {}".format(DEBUG, bkt))
                    _parameters['ParameterValue'] = param_value

                if s3_replacement_requested_re.search(param_value):
                    url = self.regxfind(get_url_re, param_value)
                    param_value = self.get_s3contents(url)
                    if self.verbose:
                        print("{}Raw content of url {}".format(DEBUG, url))
                    _parameters['ParameterValue'] = param_value

                if default_keypair_requested_re.search(param_value):
                    keypair = self.regxfind(default_keypair_requested_re, param_value)
                    param_value = 'cikey'
                    if self.verbose:
                        print("{}Generating default Keypair {}".format(DEBUG, keypair))
                    _parameters['ParameterValue'] = param_value

                if default_license_bucket_requested_re.search(param_value):
                    licensebucket = self.regxfind(default_license_bucket_requested_re, param_value)
                    param_value = 'override_this'
                    if self.verbose:
                        print("{}Generating default license bucket {}".format(DEBUG, licensebucket))
                    _parameters['ParameterValue'] = param_value

                if default_media_bucket_requested_re.search(param_value):
                    media_bucket = self.regxfind(default_media_bucket_requested_re, param_value)
                    param_value = 'override_this'
                    if self.verbose:
                        print("{}Generating default media bucket {}".format(DEBUG, media_bucket))
                    _parameters['ParameterValue'] = param_value

                if license_content_requested_re.search(param_value):
                    license_str = self.regxfind(license_content_requested_re, param_value)
                    license_bucket = license_str.split('/')[1]
                    licensekey = '/'.join(license_str.split('/')[2:])
                    param_value = self.get_content(license_bucket, licensekey)
                    if self.verbose:
                        print("{}Getting license content for {}/{}".format(DEBUG, license_bucket, licensekey))
                    _parameters['ParameterValue'] = param_value

                if presigned_url_requested_re.search(param_value):
                    if len(param_value) < 2:
                        print("{}Syntax error when using $[taskcat_getpresignedurl]; Not enough parameters.".format(DEBUG))
                        print("{}Syntax: $[taskcat_presignedurl],bucket,key,OPTIONAL_TIMEOUT".format(DEBUG))
                        quit(1)
                    paramsplit = self.regxfind(presigned_url_requested_re, param_value).split(',')[1:]
                    url_bucket, url_key = paramsplit[:2]
                    if len(paramsplit) == 3:
                        url_expire_seconds = paramsplit[2]
                    else:
                        url_expire_seconds = 3600
                    if self.verbose:
                        print("{}Generating a presigned URL for {}/{} with a {} second timeout".format(DEBUG, url_bucket, url_key, url_expire_seconds))
                    s3_client = self.aws_client_factory.get('s3', region=self.get_default_region(), s3v4=True)
                    param_value = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': url_bucket, 'Key': url_key},
                        ExpiresIn=int(url_expire_seconds))
                    _parameters['ParameterValue'] = param_value

                # Autogenerated value to password input in runtime
                if generate_password_requested_re.search(param_value):
                    passlen = int(self.regxfind(password_size_re, param_value))
                    gentype = self.regxfind(password_type_re, param_value)
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
                        # A value of D will generate a simple alpha
                        # aplha numeric password
                        gentype = 'D'

                    if passlen:
                        if self.verbose:
                            print("{}AutoGen values for {}".format(DEBUG, param_value))
                        param_value = self.generate_password(passlen, gentype)
                        _parameters['ParameterValue'] = param_value

                if generate_az_requested_re.search(param_value):
                    numazs = int(self.regxfind(password_size_re, param_value))
                    if numazs:
                        if self.verbose:
                            print(DEBUG + "Selecting availability zones")
                            print(DEBUG + "Requested %s az's" % numazs)

                        param_value = self.get_available_azs(region, numazs)
                        _parameters['ParameterValue'] = param_value
                    else:
                        print(INFO + "$[taskcat_genaz_(!)]")
                        print(INFO + "Number of az's not specified!")
                        print(INFO + " - (Defaulting to 1 az)")
                        param_value = self.get_available_azs(region, 1)
                        _parameters['ParameterValue'] = param_value

                if generate_single_az_requested_re.search(param_value):
                    print(DEBUG + "Selecting availability zones")
                    print(DEBUG + "Requested 1 az")
                    param_value = self.get_available_azs(region, 1)
                    _parameters['ParameterValue'] = param_value

                self.set_parameter(param_key, param_value)

                if get_val_requested_re.search(param_value):
                    requested_key = self.regxfind(get_val_requested_re, param_value)
                    print("{}Getting previously assigned value for {}".format(DEBUG, requested_key))
                    param_value = self.get_parameter(requested_key)
                    print("{}Loading {} as value for {} ".format(DEBUG, param_value, requested_key))
                    _parameters['ParameterValue'] = param_value

        return input_parameters
