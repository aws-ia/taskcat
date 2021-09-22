import os
import unittest
from pathlib import Path
from unittest import mock

from taskcat._cli_modules.package import Package


class TestPackageCli(unittest.TestCase):
    @mock.patch(
        "taskcat._config.Boto3Cache.partition", autospec=True, return_value="aws"
    )
    @mock.patch("taskcat._lambda_build.docker", autospec=True)
    @mock.patch(
        "taskcat._cli_modules.package.LambdaBuild._build_lambdas", autospec=True
    )
    def test_package(self, m_build, m_docker, _):
        base_path = "./" if os.getcwd().endswith("/tests") else "./tests/"
        base_path = Path(base_path + "data/lambda_build_with_submodules").resolve()
        Package(project_root=base_path, config_file=base_path / ".taskcat.yml")
        self.assertEqual(m_build.call_count, 3)
        self.assertEqual(m_docker.from_env.call_count, 1)
