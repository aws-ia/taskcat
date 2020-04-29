# pylint: disable=duplicate-code
import logging
from io import BytesIO
from pathlib import Path
from time import sleep

from dulwich import porcelain
from dulwich.config import ConfigFile, parse_submodules
from taskcat._cfn.threaded import Stacker
from taskcat._client_factory import Boto3Cache
from taskcat._config import Config
from taskcat._dataclasses import Tag
from taskcat._name_generator import generate_name
from taskcat._s3_stage import stage_in_s3
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class Deploy:
    """[ALPHA] installs a stack into an AWS account/region"""

    PKG_CACHE_PATH = Path("~/.taskcat_package_cache/").expanduser().resolve()

    # pylint: disable=too-many-branches,too-many-locals
    def __init__(  # noqa: C901
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
        LOG.warning("deploy is in alpha feature, use with caution")
        boto3_cache = Boto3Cache()
        if not name:
            name = generate_name()
        if region == "default":
            region = boto3_cache.get_default_region(profile_name=aws_profile)
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
            path = Deploy.PKG_CACHE_PATH / org / repo
            LOG.info(f"fetching git repo {url}")
            self._git_clone(url, path)
            self._recurse_submodules(path, url)
        config = Config.create(
            args={"project": {"regions": [region]}},
            project_config_path=(path / ".taskcat.yml"),
            project_root=path,
        )
        # only use one region
        for test_name in config.config.tests:
            config.config.tests[test_name].regions = config.config.project.regions
        # if there's no test called default, take the 1st in the list
        if "default" not in config.config.tests:
            config.config.tests["default"] = config.config.tests[
                list(config.config.tests.keys())[0]
            ]
        # until install offers a way to run different "plans" we only need one test
        for test_name in list(config.config.tests.keys()):
            if test_name != "default":
                del config.config.tests[test_name]
        buckets = config.get_buckets(boto3_cache)
        stage_in_s3(buckets, config.config.project.name, path)
        regions = config.get_regions(boto3_cache)
        templates = config.get_templates()
        parameters = config.get_rendered_parameters(buckets, regions, templates)
        tests = config.get_tests(templates, regions, buckets, parameters)
        tags = [Tag({"Key": "taskcat-installer", "Value": name})]
        stacks = Stacker(config.config.project.name, tests, tags=tags)
        stacks.create_stacks()
        LOG.error(
            f" {stacks.uid.hex}",
            extra={"nametag": "\x1b[0;30;47m[INSTALL_ID  ]\x1b[0m"},
        )
        LOG.error(f" {name}", extra={"nametag": "\x1b[0;30;47m[INSTALL_NAME]\x1b[0m"})
        if wait:
            LOG.info(
                f"waiting for stack {stacks.stacks[0].name} to complete in "
                f"{stacks.stacks[0].region_name}"
            )
            while stacks.status()["IN_PROGRESS"]:
                sleep(5)
        if stacks.status()["FAILED"]:
            LOG.error("Install failed:")
            for error in stacks.stacks[0].error_events():
                LOG.error(f"{error.logical_id}: {error.status_reason}")
            raise TaskCatException("Stack creation failed")

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
