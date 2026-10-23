import io
import tarfile
from unittest import mock

import pytest
from taskcat._lambda_build import LambdaBuild
from taskcat.exceptions import TaskCatException


def _tar_bytes(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, linkname in members:
            info = tarfile.TarInfo(name)
            if linkname is None:
                data = b"x"
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            else:
                info.type = tarfile.SYMTYPE
                info.linkname = linkname
                tar.addfile(info)
    return buf.getvalue()


def _run_extract(tmp_path, members):
    package_path = tmp_path / "packages" / "my_function"
    container = mock.Mock()
    container.wait.return_value = {"StatusCode": 0}
    container.logs.return_value = b""
    container.get_archive.return_value = (iter([_tar_bytes(members)]), {})
    builder = LambdaBuild.__new__(LambdaBuild)
    builder._docker = mock.Mock()
    builder._docker.containers.run.return_value = container
    builder._docker_extract("tag", package_path)
    return package_path


def test_rejects_sibling_directory_member(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(TaskCatException):
        _run_extract(tmp_path, [("../my_function-evil/x", None)])
    assert not (tmp_path / "packages" / "my_function-evil").exists()


def test_rejects_symlink_pointing_outside(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(TaskCatException):
        _run_extract(tmp_path, [("output/link", "/tmp")])
