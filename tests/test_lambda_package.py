import unittest
from os import mkdir
from pathlib import Path
from shutil import copytree
from tempfile import mkdtemp
from unittest.mock import MagicMock, patch

from requests.exceptions import ReadTimeout

from dulwich.repo import Repo
from taskcat._config import Config
from taskcat._lambda_build import LambdaBuild


def m_get_archive(path):
    if path != "/output/":
        raise ValueError("Docker get_archive expected '/output/'")
    archive_file_path = (
        Path(__file__).parent
        / "data"
        / "lambda_build_with_submodules"
        / "docker_archive.tar"
    ).resolve()
    byte_list = []
    with open(archive_file_path, "rb") as archive_file:
        for byte in archive_file:
            byte_list.append(byte)
    return (byte_list, None)


class TestLambdaPackage(unittest.TestCase):
    @patch("taskcat._lambda_build.docker", autospec=True)
    def test_nested_submodules(self, m_docker):
        m_docker_container = MagicMock(
            **{
                "wait.return_value": {"StatusCode": 0},
                "get_archive.side_effect": m_get_archive,
                "remove.side_effect": ReadTimeout,
            }
        )
        m_docker_instance = MagicMock(
            **{
                "images.build.return_value": (None, ""),
                "containers.run.return_value": m_docker_container,
            }
        )
        m_docker.from_env.return_value = m_docker_instance
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

    def test__determine_relative_changes_from_commits(self):
        tmp = Path(mkdtemp())
        test_proj = (
            Path(__file__).parent / "./data/lambda_build_with_relative_commits"
        ).resolve()

        copytree(test_proj, tmp / "test")
        repo = Repo.init(tmp / "test")
        Path(tmp / "test/ex.txt").touch()
        repo.stage("ex.txt")
        initial_commit = repo.do_commit(b"initial")

        filenames = []
        for file in Path(tmp / "test").glob("**/*"):
            if file.is_file():
                filenames.append(file.relative_to(Path(tmp / "test")))

        repo.stage(filenames)
        second_commit = repo.do_commit(b"second")

        mkdir(f"{tmp}/test/ExampleNoPackage")
        Path(f"{tmp}/test/ExampleNoPackage/lambda_function.py").touch()

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

        LambdaBuild(
            c,
            project_root=(tmp / "test").resolve(),
            from_ref=initial_commit,
            to_ref=second_commit,
        )
        path = tmp / "test"
        zip_suffix = Path("lambda_functions") / "packages" / "TestFunc" / "lambda.zip"
        self.assertEqual((path / "lambda_functions" / "packages").is_dir(), True)
        self.assertEqual((path / zip_suffix).is_file(), True)

        zip_suffix = (
            Path("lambda_functions") / "packages" / "ExampleNoPackage" / "lambda.zip"
        )
        self.assertEqual((path / zip_suffix).is_file(), False)

    def test__determine_relative_changes_from_commits_submodules(self):
        tmp = Path(mkdtemp())
        test_proj = (
            Path(__file__).parent / "./data/lambda_build_with_relative_commits"
        ).resolve()

        copytree(test_proj, tmp / "test")
        repo = Repo.init(tmp / "test")
        Path(tmp / "test/ex.txt").touch()
        repo.stage("ex.txt")
        initial_commit = repo.do_commit(b"initial")

        filenames = []
        for file in Path(tmp / "test").glob("**/*"):
            if file.is_file():
                filenames.append(file.relative_to(Path(tmp / "test")))

        repo.stage(filenames)
        second_commit = repo.do_commit(b"second")

        mkdir(f"{tmp}/test/ExampleNoPackage")
        Path(f"{tmp}/test/ExampleNoPackage/lambda_function.py").touch()

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

        LambdaBuild(
            c,
            project_root=(tmp / "test").resolve(),
            from_ref=initial_commit,
            to_ref=second_commit,
        )
        path = tmp / "test"
        zip_suffix = Path("lambda_functions") / "packages" / "TestFunc" / "lambda.zip"
        self.assertEqual((path / "lambda_functions" / "packages").is_dir(), True)
        self.assertEqual((path / zip_suffix).is_file(), True)

        zip_suffix = (
            Path("lambda_functions") / "packages" / "ExampleNoPackage" / "lambda.zip"
        )
        self.assertEqual((path / zip_suffix).is_file(), False)

        zip_suffix = Path("lambda_functions") / "packages" / "TestFunc" / "lambda.zip"
        path = path / "submodules" / "SomeSub"
        self.assertEqual((path / "lambda_functions" / "packages").is_dir(), True)
        self.assertEqual((path / zip_suffix).is_file(), True)

        path = path / "submodules" / "DeepSub"
        self.assertEqual((path / "lambda_functions" / "packages").is_dir(), True)
        self.assertEqual((path / zip_suffix).is_file(), True)
