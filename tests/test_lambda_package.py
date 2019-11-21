import unittest
from pathlib import Path
from shutil import copytree
from tempfile import mkdtemp

from taskcat._config import Config
from taskcat._lambda_build import LambdaBuild


class TestLambdaPackage(unittest.TestCase):
    def test_nested_submodules(self):
        tmp = Path(mkdtemp())
        test_proj = (
            Path(__file__).parent / "./data/lambda_build_with_submodules"
        ).resolve()
        copytree(test_proj, tmp / "test")
        c = Config.create(
            project_config_path=tmp / "test" / ".taskcat.yml",
            project_root=(tmp / "test").resolve(),
            args={
                "project": {
                    "lambda_zip_path": "lambda_functions/packages",
                    "lambda_source_path": "lambda_functions/source",
                }
            },
        )
        LambdaBuild(c, project_root=(tmp / "test").resolve())
        path = tmp / "test"
        zip_suffix = Path("lambda_functions") / "packages" / "TestFunc" / "lambda.zip"
        self.assertEqual((path / "lambda_functions" / "packages").is_dir(), True)
        self.assertEqual((path / zip_suffix).is_file(), True)
        path = path / "submodules" / "SomeSub"
        self.assertEqual((path / "lambda_functions" / "packages").is_dir(), True)
        self.assertEqual((path / zip_suffix).is_file(), True)
        path = path / "submodules" / "DeepSub"
        self.assertEqual((path / "lambda_functions" / "packages").is_dir(), True)
        self.assertEqual((path / zip_suffix).is_file(), True)
