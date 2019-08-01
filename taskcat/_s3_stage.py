import logging

from taskcat._s3_sync import S3Sync
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class S3APIResponse:
    def __init__(self, x):
        self._http_code = x["ResponseMetadata"]["HTTPStatusCode"]

    @property
    def ok(self):
        if self._http_code == 200:
            return True
        return False


class S3BucketCreatorException(TaskCatException):
    pass


def stage_in_s3(config):
    """
    Upload templates and other artifacts to s3.

    This function creates the s3 bucket with name provided in the config yml file. If
    no bucket name provided, it creates the s3 bucket using project name provided in
    config yml file. And uploads the templates and other artifacts to the s3 bucket.

    :param config: Taskcat config object.

    """
    bucket_set: set = set()

    for test in config.tests.values():
        for region in test.regions:
            bucket_set.add(region.s3bucket)
    for bucket in bucket_set:
        bucket.create()
    for bucket in bucket_set:
        S3Sync(bucket.client, bucket.name, config.name, config.project_root, bucket.acl)
