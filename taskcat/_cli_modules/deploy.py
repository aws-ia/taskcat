# pylint: disable=duplicate-code
import logging
from io import BytesIO
from pathlib import Path
import boto3

from dulwich import porcelain
from dulwich.config import ConfigFile, parse_submodules
from taskcat._cli_modules.test import Test
from taskcat._name_generator import generate_name
from taskcat._cfn.threaded import Stacker
from taskcat.regions_to_partitions import REGIONS

LOG = logging.getLogger(__name__)


class Deploy:
    """[ALPHA] installs a stack into an AWS account/regions"""

    PKG_CACHE_PATH = Path("~/.taskcat_package_cache/").expanduser().resolve()

    # pylint: disable=too-many-branches,too-many-locals
    def run(  # noqa: C901
        self,
        package: str = "./",
        test_names: str = "ALL",
        regions: str = "ALL",
        name="",
        input_file: str = "./.taskcat.yml",
    ):
        """
        :param package: name of package to install can be a path to a local package,
        a github org/repo, or an AWS Quick Start name
        :param test_names: comma separated list of tests to run
        :param regions: comma separated list of regions to test in
        default
        :param name: stack name to use, if not specified one will be automatically
        generated
        :param input_file: path to either a taskcat project config file or a CloudFormation template
        """
        LOG.warning("deploy is in alpha feature, use with caution")
        if not name:
            name = generate_name()
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
                org, repo = package.replace(".git", "").replace(":", "/").split("/")[-2:]
            else:
                org, repo = package.split("/")
                url = f"https://github.com/{org}/{repo}.git"
            path = Deploy.PKG_CACHE_PATH / org / repo
            LOG.info(f"fetching git repo {url}")
            self._git_clone(url, path)
            self._recurse_submodules(path, url)

        Test.run(regions=regions, no_delete=True, project_root=path, test_names=test_names)

    @staticmethod
    def _git_clone(url, path):
        outp = BytesIO()
        if path.exists():
            # TODO: handle updating existing repo
            LOG.warning("path already exists, updating from remote is not yet implemented")
            # shutil.rmtree(path)
        if not path.exists():
            path.mkdir(parents=True)
            porcelain.clone(url, str(path), checkout=True, errstream=outp, outstream=outp)
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

    def list(self, region: str = "ALL", project: str = "none", aws_profile="default", no_verify=False):
        """
        Lists identifiers for stacks deployed with taskcat deploy. Stacks deployed with taskcat test run -n
        will not be listed with this command
        :param region: names of regions from which to list the taskcat stacks' identifiers
        :param project: name of projects from which to list the taskcat stacks' identifiers
        :param no-verify: whether to verify supplied regions
        """
        if region == "ALL":
            region_set: set = set()
            region_set = region_set.union(
                # pylint: disable=duplicate-code
                set(
                    boto3.Session(profile_name=aws_profile).get_available_regions(
                        "cloudformation"
                    )
                )
            )
            regions = list(region_set)
        elif isinstance(region, str):
            regions = self._validate_regions(region) if not no_verify else region.split(",")
        stacks = Stacker.list_stacks([aws_profile], regions)
        LOG.info("Stacks:")
        for stack in stacks:
            job = {
                "project_name": stack["taskcat-project-name"],
                "stack_name": stack["stack-name"],
                "taskcat_id": stack["taskcat-id"].hex,
                "region": stack["region"],
            }
            LOG.info(job)

    # Checks if all regions are valid
    def _validate_regions(self, region_string):
        regions = region_string.split(",")
        for region in regions:
            if region not in REGIONS:
                LOG.error(f"Bad region detected: {region}")
                exit(1)
        return regions
