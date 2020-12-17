import unittest
from abc import ABC

from taskcat.testing._abstract_test import Test


class TestAbstractTest(unittest.TestCase):

    Test.__abstractmethods__ = set()

    def test_properties(self):
        test = Test()

        self.assertIsNone(test.config, "Checks if config is a required propetry.")
        self.assertIsNone(test.passed, "Checks if passed is a required propetry.")
        self.assertIsNone(test.result, "Checks if passed is a required propetry.")

    def test_methods(self):
        test = Test()

        self.assertIsNone(test.run(), "Checks if run is a required method.")
        self.assertIsNone(test.clean_up(), "Checks if clean_up is a required method.")
        self.assertIsNone(test.__enter__(), "Checks if __enter__ is a required method.")

    def test_inheritance(self):
        test = Test()

        self.assertIsInstance(test, ABC)
