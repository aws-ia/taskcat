import os
import shutil
import unittest
∏
from ruamel.yaml import YAML
from taskcat._cli_modules.generate_config import GenerateConfig
from taskcat.exceptions import TaskCatException

yaml = YAML()
yaml.preserve_quotes = True


class TestGenerateConfig(unittest.TestCase):
    main_template = "tests/data/standalone_template/test.template_w_parameters.yaml"
    source_file = "tests/data/config_output/cfg_source/.taskcat.yaml"

    def test_generate_config_no_template(self):
        with self.assertRaises(TaskCatException):
            GenerateConfig(main_template="test.yaml")

    def test_generate_config_no_output_file(self):
        with self.assertRaises(TaskCatException):
            GenerateConfig(main_template="test.yaml", project_root="/testroot")

    def test_generate_config_with_config_present(self):
        # Setup
        src = "tests/data/config_output/cfg_source/.taskcat.yaml"
        dest = "tests/data/config_output/.taskcat.yaml"
        shutil.copy(src, dest)
        # ********
        output_file = "tests/data/config_output/.taskcat.yaml"
        with self.assertRaises(TaskCatException):
            GenerateConfig(main_template=self.main_template, output_file=output_file)
        os.remove(dest)

    def test_generate_config_with_config_present_and_replace(self):
        # Setup
        src = "tests/data/config_output/cfg_source/.taskcat.yaml"
        dest = "tests/data/config_output/.taskcat.yaml"
        shutil.copy(src, dest)
        # ********
        output_file = "tests/data/config_output/.taskcat.yaml"
        GenerateConfig(
            main_template=self.main_template, output_file=output_file, replace=True
        )
        self.assertEqual(
            os.stat(output_file).st_size, os.stat(self.source_file).st_size
        )
        os.remove(dest)

    def test_generate_config_with_empty_config_present(self):
        # Setup
        src = "tests/data/config_output/cfg_source/.taskcat_empty.yaml"
        shutil.copy(src, "tests/data/config_output/.taskcat.yaml")
        # ********
        output_file = "tests/data/config_output/.taskcat.yaml"
        GenerateConfig(main_template=self.main_template, output_file=output_file)
        self.assertEqual(
            os.stat(output_file).st_size, os.stat(self.source_file).st_size
        )
        os.remove(output_file)
