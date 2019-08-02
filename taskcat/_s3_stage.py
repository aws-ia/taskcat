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

    # Create the bucket objects first!
    for test in config.tests.values():
        for region in test.regions:
            bucket_set.add(region.s3bucket)
    # Sync!
    for bucket in bucket_set:
        try:
            bucket.create()
        except Exception as e:
            raise TaskCatException(e)

    for bucket in bucket_set:
        S3Sync(
            bucket.client("s3"),
            bucket.name,
            config.name,
            config.project_root,
            bucket.acl,
        )


# pylint: disable=line-too-long
# self.s3_url_prefix = "https://" + self.get_s3_hostname() + "/" + self.get_project_name()
