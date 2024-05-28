import unittest
import os
from ruamel.yaml import YAML
from taskcat._cli_modules.generate_config import GenerateConfig
from taskcat.exceptions import TaskCatException
yaml = YAML()
yaml.preserve_quotes = True


class TestGenerateConfig(unittest.TestCase):
    def test_generate_config_no_template(self):
        with self.assertRaises(TaskCatException):
            GenerateConfig(main_template="test.yaml")
    
    def test_generate_config_no_output_file(self):
        with self.assertRaises(TaskCatException):
            GenerateConfig(main_template="test.yaml", project_root="/testroot")

    def test_generate_config_with_config_present(self):
        main_template = "tests/data/standalone_template/test.template_w_parameters.yaml"
        output_file = ".taskcat_w_parameters.yaml"
        with self.assertRaises(TaskCatException):
            GenerateConfig(main_template=main_template, output_file=output_file)

    def test_generate_config_with_config_present_and_replace(self):
        main_template = "tests/data/standalone_template/test.template_w_parameters.yaml"
        output_file = "tests/data/config_output/.taskcat_w_parameters_test.yaml"
        source_file = "tests/data/config_output/.taskcat_w_parameters.yaml"
        GenerateConfig(main_template=main_template, output_file=output_file, replace=True)
        self.assertEqual(
            os.stat(output_file).st_size,
            os.stat(source_file).st_size
        )
        os.remove(output_file)
