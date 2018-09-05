import random

from .formatter import DEBUG

class PasswordGenerator:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def generate(self, length, type_):
        """
        Returns a password of given length and type.

        :param length: Length of the desired password
        :param type_: Type of the desired password - String only OR Alphanumeric
            * A = AlphaNumeric, Example 'vGceIP8EHC'
        :return: Password of given length and type
        """
        if self.verbose:
            print(DEBUG + "Auto generating password")
            print(DEBUG + "Pass size => {0}".format(length))

        password = []
        numbers = "1234567890"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        specialchars = "!#$&{*:[=,]-_%@+"

        # Generates password string with:
        # lowercase,uppercase and numeric chars
        if type_ == 'A':
            print(DEBUG + "Pass type => {0}".format('alpha-numeric'))

            while len(password) < length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        # Generates password string with:
        # lowercase,uppercase, numbers and special chars
        elif type_ == 'S':
            print(DEBUG + "Pass type => {0}".format('specialchars'))
            while len(password) < length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))
                password.append(random.choice(specialchars))
        else:
            # If no passtype is defined (None)
            # Defaults to alpha-numeric
            # Generates password string with:
            # lowercase,uppercase, numbers and special chars
            print(DEBUG + "Pass type => default {0}".format('alpha-numeric'))
            while len(password) < length:
                password.append(random.choice(lowercase))
                password.append(random.choice(uppercase))
                password.append(random.choice(numbers))

        return ''.join(password)
