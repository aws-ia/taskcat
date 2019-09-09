import os
import unittest
from pathlib import Path

from taskcat._config import Config


class TestConfig(unittest.TestCase):
    def test_config(self):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/").resolve()

        # ingest config with args:
        config = Config(
            project_config_path=base_path
            / "standalone_template_no_metadata/test.template.yaml",
            project_root=base_path / "standalone_template_no_metadata",
            create_clients=False,
            args={
                "template_file": "test.template.yaml",
                "regions": "us-east-1",
                "parameter_input": "params.json",
                "no_cleanup": True,
            },
        )
        self.assertEqual(
            config.tests["default"].template_file.name, "test.template.yaml"
        )
        self.assertEqual(config.no_cleanup, True)

        for config_path, project_root in [
            [None, base_path / "create_fail"],
            [base_path / "delete_fail/ci/taskcat.yml", base_path / "delete_fail"],
            [
                base_path / "lambda_build_with_submodules/.taskcat.yml",
                base_path / "lambda_build_with_submodules",
            ],
            [base_path / "lint-error/.taskcat.yml", base_path / "lint-error"],
            [base_path / "lint-warning/.taskcat.yml", base_path / "lint-warning"],
            [base_path / "nested-fail/ci/taskcat.yml", base_path / "nested-fail"],
            [
                base_path / "regional_client_and_bucket/ci/taskcat.yml",
                base_path / "regional_client_and_bucket",
            ],
            [
                base_path / "standalone_template_no_metadata/test.template.yaml",
                base_path / "standalone_template_no_metadata",
            ],
        ]:
            print(f"testing {config_path} {project_root}")  # noqa: T001
            Config(
                project_config_path=config_path,
                project_root=project_root,
                create_clients=False,
            )

            # Nothing to assert, as this test is just ensuring that the config can
            # ingest all the sample configs
