import unittest
import json
from taskcat import InputParameterGenerator

TEST_INPUT_FILE = 'tests/test_data/test_parameter_file.json'
TEST_REGION = 'us-east-1'


# We are not testing the password generator, so this doesn't matter here
class MockPasswordGenerator:
    def generate(self, length, type_):
        return 'DUMMY_PASSWORD_TEST'


class InputParameterGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.generator = InputParameterGenerator(
            password_generator=MockPasswordGenerator(),
            parameter_file=TEST_INPUT_FILE,
            verbose=True)

    def test_parameter_generator_generates_parameters(self):
        generated_parameters = self.generator.generate(
                self._load_test_inputs(),
                TEST_REGION
        )
        self._assertNotEmpty(generated_parameters)
        self._assertParametersChanged(generated_parameters)

    def _load_test_inputs(self):
        with open(TEST_INPUT_FILE) as f:
            return json.load(f)

    def _assertNotEmpty(self, value):
        self.assertNotEqual(len(value), 0)

    def _assertParametersChanged(self, parameters):
        self.assertNotEqual(parameters, self._load_test_inputs())
