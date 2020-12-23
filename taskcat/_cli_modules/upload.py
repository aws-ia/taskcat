import logging
from pathlib import Path
from typing import Any, Dict

from taskcat._cli_core import CliCore
from taskcat._client_factory import Boto3Cache
from taskcat._config import Config
from taskcat._lambda_build import LambdaBuild
from taskcat._s3_stage import stage_in_s3

LOG = logging.getLogger(__name__)


class Upload:
    """
    Uploads project to S3.
    """

    @CliCore.longform_param_required("dry_run")
    def __init__(
        self,
        config_file: str = "./.taskcat.yml",
        project_root: str = "./",
        enable_sig_v2: bool = False,
        bucket_name: str = "",
        disable_lambda_packaging: bool = False,
        key_prefix: str = "",
        dry_run: bool = False,
    ):
        """does lambda packaging and uploads to s3

        :param config_file: path to taskat project config file
        :param enable_sig_v2: enable legacy sigv2 requests for auto-created buckets
        :param bucket_name: set bucket name instead of generating it. If regional
        buckets are enabled, will use this as a prefix
        :param disable_lambda_packaging: skip packaging step
        :param key_prefix: provide a custom key-prefix for uploading to S3. This
        will be used instead of `project` => `name` in the config
        :param dry_run: identify changes needed but do not upload to S3.
        """
        project_root_path: Path = Path(project_root).expanduser().resolve()
        input_file_path: Path = project_root_path / config_file
        args: Dict[str, Any] = {"project": {"s3_enable_sig_v2": enable_sig_v2}}
        if bucket_name:
            args["project"]["bucket_name"] = bucket_name
        if key_prefix:
            args["project"]["name"] = key_prefix
        config = Config.create(
            project_root=project_root_path,
            project_config_path=input_file_path,
            args=args,
        )
        boto3_cache = Boto3Cache()
        if (
            config.config.project.package_lambda
            and disable_lambda_packaging is not True
        ):
            LambdaBuild(config, project_root_path)
        buckets = config.get_buckets(boto3_cache)
        stage_in_s3(buckets, config.config.project.name, config.project_root, dry_run)
