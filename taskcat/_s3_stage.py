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


def stage_in_s3(buckets, project_name, project_root):
    distinct_buckets = {}

    for test in buckets.values():
        for bucket in test.values():
            distinct_buckets[bucket.name] = bucket
    for bucket in distinct_buckets.values():
        S3Sync(
            bucket.s3_client, bucket.name, project_name, project_root, bucket.object_acl
        )
