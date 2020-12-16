import unittest
from abc import ABC

from taskcat.testing.ab_test import Test


class TestAbstractTest(unittest.TestCase):

    Test.__abstractmethods__ = set()

    def test_properties(self):
        test = Test()

        self.assertIsNone(test.config, "Checks if config is a propetry of Test.")
        self.assertIsNone(test.passed, "Checks if passed is a propetry of Test.")
        self.assertIsNone(test.result, "Checks if passed is a propetry of Test.")

    def test_methods(self):
        test = Test()

        self.assertIsNone(test.run(), "Checks if config is a propetry of Test.")
        self.assertIsNone(test.clean_up(), "Checks if passed is a propetry of Test.")

    def test_inheritance(self):
        test = Test()

        self.assertIsInstance(test, ABC)
