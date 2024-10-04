import logging
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool

from taskcat._s3_sync import S3Sync
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class S3APIResponse:
    def __init__(self, _x):
        self._http_code = _x["ResponseMetadata"]["HTTPStatusCode"]

    @property
    def ok(self):
        if self._http_code == 200:
            return True
        return False


class S3BucketCreatorException(TaskCatException):
    pass


def stage_in_s3(
    buckets, project_name, project_root, exclude_prefix, dry_run=False, all_files=False
):
    distinct_buckets = {}

    for test in buckets.values():
        for bucket in test.values():
            distinct_buckets[f"{bucket.name}-{bucket.partition}"] = bucket
    pool = ThreadPool(32)
    func = partial(
        _sync_wrap,
        project_name=project_name,
        project_root=project_root,
        dry_run=dry_run,
        exclude_prefix=exclude_prefix,
        all_files=all_files,
    )
    pool.map(func, distinct_buckets.values())
    pool.close()
    pool.join()


def _sync_wrap(bucket, project_name, project_root, dry_run, exclude_prefix, all_files):
    if exclude_prefix:
        S3Sync.exclude_remote_path_prefixes += exclude_prefix
        S3Sync.exclude_path_prefixes += exclude_prefix
    if all_files:
        S3Sync.exclude_files = [".taskcat.yml"]
        S3Sync.exclude_path_prefixes = []
        S3Sync.exclude_remote_path_prefixes = []
    S3Sync(
        bucket.s3_client,
        bucket.name,
        project_name,
        project_root,
        bucket.object_acl,
        dry_run=dry_run,
    )
