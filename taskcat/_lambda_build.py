import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from subprocess import PIPE, CalledProcessError, run as subprocess_run  # nosec
from uuid import UUID, uuid5

from requests.exceptions import ReadTimeout

import docker
from docker import APIClient
from dulwich.diff_tree import tree_changes
from dulwich.errors import NotGitRepository
from dulwich.repo import Repo

from ._config import Config
from .exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class LambdaBuild:
    NULL_UUID = UUID("{00000000-0000-0000-0000-000000000000}")

    def __init__(
        self,
        config: Config,
        project_root: Path,
        from_ref: str = None,
        to_ref: str = None,
        single_package_name: str = None,
    ):
        self._dirs_with_changes = set()
        self._docker = docker.from_env()
        self._config = config
        self._project_root = Path(project_root).expanduser().resolve()
        self._lambda_source_path = (
            self._project_root / config.config.project.lambda_source_path
        ).resolve()
        self._lambda_zip_path = (
            self._project_root / config.config.project.lambda_zip_path
        ).resolve()
        self._single_package_path = None
        if single_package_name:
            self._single_package_path = Path(
                self._lambda_source_path / single_package_name
            ).resolve()
        self._determine_relative_changes_from_commits(from_ref, to_ref)
        self._build_lambdas(self._lambda_source_path, self._lambda_zip_path)
        self._build_submodules()

    def _determine_relative_changes_from_commits(self, from_ref, to_ref):  # noqa: C901
        if (not from_ref) or (not to_ref):
            return

        try:
            _r = Repo(self._project_root)
        except NotGitRepository as ngr:
            raise TaskCatException(
                f"Directory ({self._project_root}) is not a git repository"
            ) from ngr

        for change in tree_changes(_r.object_store, _r[from_ref].tree, _r[to_ref].tree):
            if change.type in ["add", "modify"]:
                _c = Path(self._project_root / change.new.path.decode()).resolve()
                if self._single_package_path:
                    if _c.parent != self._single_package_path:
                        continue
                self._dirs_with_changes.add(_c.parent)
            if change.type in ["delete"]:
                _c = Path(self._project_root / change.old.path.decode()).resolve()
                if self._single_package_path:
                    if _c.parent != self._single_package_path:
                        continue
                self._dirs_with_changes.add(_c.parent)

    def _build_submodules(self):
        if not self._config.config.project.build_submodules:
            return
        rel_source = self._lambda_source_path.relative_to(self._project_root)
        rel_zip = self._lambda_zip_path.relative_to(self._project_root)
        self._recurse(self._project_root, rel_source, rel_zip)

    def _recurse(self, base_path, rel_source, rel_zip):
        submodules_path = Path(base_path) / "submodules"
        if not submodules_path.is_dir():
            return
        for submodule in submodules_path.iterdir():
            source_path = submodule / rel_source
            if not source_path.is_dir():
                continue
            output_path = submodule / rel_zip
            self._dirs_with_changes = set()
            self._build_lambdas(source_path, output_path)
            self._recurse(submodule, rel_source, rel_zip)

    def _build_lambdas(self, parent_path: Path, output_path):
        if not parent_path.is_dir():
            return
        for path in parent_path.iterdir():
            if path.is_file():
                LOG.warning(f"{path} is a file, not a directory, cannot package...")
                continue
            if self._dirs_with_changes:
                _pd = Path(path).resolve()
                if _pd not in self._dirs_with_changes:
                    continue
            if self._single_package_path:
                if path != self._single_package_path:
                    continue
            if (path / "Dockerfile").is_file():
                tag = f"taskcat-build-{uuid5(self.NULL_UUID, str(path)).hex}"
                LOG.info(
                    f"Packaging lambda source from {path} using docker image {tag}"
                )
                self._docker_build(path, tag)
                self._docker_extract(tag, output_path / path.stem)
            elif (path / "requirements.txt").is_file():
                LOG.info(f"Packaging python lambda source from {path} using pip")
                self._pip_build(path, output_path / path.stem)
            else:
                LOG.info(
                    f"Packaging lambda source from {path} without building "
                    f"dependencies"
                )
                self._zip_dir(path, output_path / path.stem)

    @staticmethod
    def _make_pip_command(base_path):
        return [
            "pip",
            "install",
            "--no-cache-dir",
            "--no-color",
            "--disable-pip-version-check",
            "--upgrade",
            "--requirement",
            str(base_path / "requirements.txt"),
            "--target",
            str(base_path),
        ]

    @classmethod
    def _pip_build(cls, base_path, output_path):
        tmp_path = Path(tempfile.mkdtemp())
        try:
            build_path = tmp_path / "build"
            shutil.copytree(base_path, build_path)
            command = cls._make_pip_command(build_path)
            LOG.debug("command is '%s'", command)

            LOG.info("Starting pip build.")
            try:
                completed_proc = subprocess_run(  # nosec
                    command, cwd=build_path, check=True, stdout=PIPE, stderr=PIPE
                )
            except (FileNotFoundError, CalledProcessError) as e:
                raise TaskCatException("pip build failed") from e
            LOG.debug("--- pip stdout:\n%s", completed_proc.stdout)
            LOG.debug("--- pip stderr:\n%s", completed_proc.stderr)
            cls._zip_dir(build_path, output_path)
            shutil.rmtree(tmp_path, ignore_errors=True)
        except Exception as e:  # pylint: disable=broad-except
            shutil.rmtree(tmp_path, ignore_errors=True)
            raise e

    @staticmethod
    def _zip_dir(build_path, output_path):
        output_path.mkdir(parents=True, exist_ok=True)
        zip_path = output_path / "lambda.zip"
        if zip_path.is_file():
            zip_path.unlink()
        shutil.make_archive(output_path / "lambda", "zip", build_path)

    @staticmethod
    def _docker_build(path, tag):
        cli = APIClient()
        build_logs = []
        for line in cli.build(path=str(path), tag=tag):
            build_logs.append(line)
        output = []
        for line in build_logs:
            output.append(line.decode("utf-8").strip())
        LOG.debug("docker build logs: \n{}".format("\n".join(output)))

    def _docker_extract(self, tag, package_path):
        container = self._docker.containers.run(image=tag, detach=True)
        exit_code = container.wait()["StatusCode"]
        logs = container.logs()
        LOG.debug("docker run logs: \n{}".format(logs.decode("utf-8").strip()))
        if exit_code != 0:
            raise TaskCatException("docker build failed")
        arc, _ = container.get_archive("/output/")
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            for chunk in arc:
                tmpfile.write(chunk)
        with tarfile.open(tmpfile.name) as tar:
            for member in tar.getmembers():
                if member.name.startswith("output/"):
                    member.name = member.name[len("output/") :]
                    tar.extract(member)
            tar.extractall(path=str(package_path))
        try:
            container.remove()
        except ReadTimeout:
            LOG.warning(f"Could not remove container {container.id}")
        os.unlink(tmpfile.name)
        os.removedirs(str(package_path / "output"))
