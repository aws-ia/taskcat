import logging
import shutil
from io import BytesIO
from pathlib import Path
from dulwich import porcelain
from dulwich.repo import Repo
from dulwich.config import parse_submodules, ConfigFile

from taskcat._client_factory import ClientFactory
from taskcat._cfn.threaded import Stacker
from taskcat._name_generator import generate_name
from taskcat._config_types import AWSRegionObject, S3Bucket
from taskcat.exceptions import TaskCatException
from taskcat._config import Config
from taskcat._s3_stage import stage_in_s3

LOG = logging.getLogger(__name__)


class Install:
    """installs a stack into an AWS account/region"""

    PKG_CACHE_PATH = Path("~/.taskcat_package_cache/").expanduser().resolve()

    def __init__(
        self,
        package: str,
        aws_profile: str = "default",
        region="default",
        parameters="",
        name="",
        wait=False,
    ):
        """
        :param package: name of package to install can be a path to a local package,
        a github org/repo, or an AWS Quick Start name
        :param aws_profile: aws profile to use for installation
        :param region: regions to install into, default will use aws cli configured
        default
        :param parameters: parameters to pass to the stack, in the format
        Key=Value,AnotherKey=AnotherValue or providing a path to a json or yaml file
        containing the parameters
        :param name: stack name to use, if not specified one will be automatically
        generated
        :param wait: if enabled, taskcat will wait for stack to complete before exiting
        """
        if not name:
            name = generate_name()
        if region == "default":
            region = ClientFactory.get_default_region(
                None, None, None, profile_name=aws_profile
            )
        path = Path(package).resolve()
        if Path(package).resolve().is_dir():
            package_type = "local"
        elif "/" in package:
            package_type = "github"
        else:  # assuming it's an AWS Quick Start
            package_type = "github"
            package = f"aws-quickstart/quickstart-{package}"
        if package_type == "github":
            if package.startswith("https://") or package.startswith("git@"):
                url = package
                org, repo = (
                    package.replace(".git", "").replace(":", "/").split("/")[-2:]
                )
            else:
                org, repo = package.split("/")
                url = f"https://github.com/{org}/{repo}.git"
            path = Install.PKG_CACHE_PATH / org / repo
            LOG.info(f"fetching git repo {url}")
            self._git_clone(url, path)
            self._recurse_submodules(path, url)
        config = Config(
            args={"regions": region},
            project_config_path=(path / ".taskcat.yml"),
            project_root=path,
        )
        stage_in_s3(config)

    def _git_clone(self, url, path):
        outp = BytesIO()
        if path.exists():
            # TODO: handle updating existing repo
            LOG.warning(
                "path already exists, updating from remote is not yet implemented"
            )
            # shutil.rmtree(path)
        if not path.exists():
            path.mkdir(parents=True)
            porcelain.clone(
                url, str(path), checkout=True, errstream=outp, outstream=outp
            )
        LOG.debug(outp.getvalue().decode("utf-8"))

    def _recurse_submodules(self, path: Path, parent_url):
        gitmodule_path = path / ".gitmodules"
        if not gitmodule_path.is_file():
            return
        cf = ConfigFile.from_path(str(gitmodule_path))
        for sub_path, url, name in parse_submodules(cf):
            sub_path = sub_path.decode("utf-8")
            url = url.decode("utf-8")
            name = name.decode("utf-8")
            if not (path / sub_path).is_dir():
                (path / sub_path).mkdir(parents=True)
            # bizarre process here, but I don't know how else to get the sha for the submodule...
            sha = None
            try:
                porcelain.get_object_by_path(str(path), sub_path)
            except KeyError as e:
                sha = e.args[0].decode("utf-8")
            if not sha:
                raise ValueError(f"Could not find sha for submodule {name}")
            if url.startswith("../"):
                base_url = parent_url
                for _ in range(url.count("../")):
                    base_url = "/".join(base_url.split("/")[:-1])
                url = base_url + "/" + url.replace("../", "")
            outp = BytesIO()
            if not (path / sub_path / ".git").is_dir():
                LOG.info(f"fetching git submodule {url}")
                porcelain.clone(
                    url,
                    str(path / sub_path),
                    checkout=sha,
                    errstream=outp,
                    outstream=outp,
                )
                LOG.debug(outp.getvalue().decode("utf-8"))
            self._recurse_submodules((path / sub_path), url)
