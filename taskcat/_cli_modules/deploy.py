# pylint: disable=duplicate-code
import logging
import sys
from io import BytesIO
from pathlib import Path

from dulwich import porcelain
from dulwich.config import ConfigFile, parse_submodules
from taskcat._cli_modules.test import Test
from taskcat._dataclasses import Tag
from taskcat._name_generator import generate_name
from taskcat.regions_to_partitions import REGIONS

from .list import List

LOG = logging.getLogger(__name__)


class Deploy:
    """[ALPHA] installs a stack into an AWS account/regions"""

    PKG_CACHE_PATH = Path("~/.taskcat_package_cache/").expanduser().resolve()

    # pylint: disable=too-many-branches,too-many-locals
    def run(  # noqa: C901
        self,
        project: str = "./",
        test_names: str = "ALL",
        regions: str = "ALL",
        name="",
        input_file: str = "./.taskcat.yml",
    ):
        """
        :param project: name of project to install can be a path to a local project,\
        a github org/repo, or an AWS Quick Start name
        :param test_names: comma separated list of tests (specified in .taskcat.yml) to run\
            defaults to the 'default' test. Set to 'ALL' to deploy every entry
        :param regions: comma separated list of regions to test in\
        default
        :param name: stack name to use, if not specified one will be automatically\
        generated
        :param input_file: path to either a taskcat project config file or a CloudFormation template
        """
        if not name:
            name = generate_name()
        path = Path(project).resolve()
        if Path(project).resolve().is_dir():
            package_type = "local"
        elif "/" in project:
            package_type = "github"
        else:  # assuming it's an AWS Quick Start
            package_type = "github"
            project = f"aws-quickstart/quickstart-{project}"
        if package_type == "github":
            if project.startswith("https://") or project.startswith("git@"):
                url = project
                org, repo = (
                    project.replace(".git", "").replace(":", "/").split("/")[-2:]
                )
            else:
                org, repo = project.split("/")
                url = f"https://github.com/{org}/{repo}.git"
            path = Deploy.PKG_CACHE_PATH / org / repo
            LOG.info(f"fetching git repo {url}")
            self._git_clone(url, path)
            self._recurse_submodules(path, url)
        _extra_tags = [(Tag({"Key": "taskcat-installer", "Value": name}))]
        Test.run(
            regions=regions,
            no_delete=True,
            project_root=path,
            test_names=test_names,
            input_file=input_file,
            _extra_tags=_extra_tags,
        )

    @staticmethod
    def _git_clone(url, path):
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
        conf = ConfigFile.from_path(str(gitmodule_path))
        for sub_path, url, name in parse_submodules(conf):
            sub_path = sub_path.decode("utf-8")
            url = url.decode("utf-8")
            name = name.decode("utf-8")
            if not (path / sub_path).is_dir():
                (path / sub_path).mkdir(parents=True)
            # bizarre process here, but I don't know how else to get the sha for the
            # submodule...
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

    @staticmethod
    def list(profiles: str = "default", regions="ALL"):
        """
        :param profiles: comma separated list of aws profiles to search
        :param regions: comma separated list of regions to search, default is to check
        all commercial regions
        """
        List(profiles=profiles, regions=regions, stack_type="project")

    # Checks if all regions are valid
    @staticmethod
    def _validate_regions(region_string):
        regions = region_string.split(",")
        for region in regions:
            if region not in REGIONS:
                LOG.error(f"Bad region detected: {region}")
                sys.exit(1)
        return regions
