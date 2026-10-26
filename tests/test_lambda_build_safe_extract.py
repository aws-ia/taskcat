import io
import tarfile
from unittest import mock

import pytest
from taskcat._lambda_build import LambdaBuild
from taskcat.exceptions import TaskCatException


def _tar_bytes(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, kind, linkname in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                data = b"x"
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
                continue
            if kind == "dir":
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = linkname
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
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


@pytest.fixture(params=["data_filter", "fallback"])
def extraction_mode(request, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    if request.param == "fallback":
        monkeypatch.delattr(tarfile, "data_filter", raising=False)
    return request.param


@pytest.mark.parametrize(
    "members",
    [
        pytest.param([("../my_function-evil/x", "file", None)], id="sibling-dir"),
        pytest.param(
            [("/abs/packages/my_function-evil/x", "file", None)], id="absolute-name"
        ),
        pytest.param([("link", "symlink", "/tmp")], id="absolute-symlink"),
        pytest.param([("link", "symlink", "../../x")], id="relative-symlink-out"),
        pytest.param([("hl", "hardlink", "../../etc/x")], id="hardlink-out"),
        pytest.param(
            [("x", "symlink", "."), ("a", "symlink", "x/x/x/../..")],
            id="chained-symlink",
        ),
    ],
)
@pytest.mark.usefixtures("extraction_mode")
def test_rejects_unsafe_members(tmp_path, members):
    with pytest.raises(TaskCatException):
        _run_extract(tmp_path, members)
    assert not (tmp_path / "packages" / "my_function-evil").exists()


@pytest.mark.usefixtures("extraction_mode")
def test_extracts_safe_members(tmp_path):
    package_path = _run_extract(
        tmp_path,
        [
            ("output", "dir", None),
            ("lambda.zip", "file", None),
            ("sub", "dir", None),
            ("sub/f.py", "file", None),
            ("sub/link", "symlink", "../lambda.zip"),
        ],
    )
    assert (package_path / "lambda.zip").is_file()
    assert (package_path / "sub" / "f.py").is_file()
    assert (package_path / "sub" / "link").resolve() == (
        package_path / "lambda.zip"
    ).resolve()
