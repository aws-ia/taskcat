import json
import logging

from taskcat._config import Config, S3BucketConfig
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


class S3BucketCreator:
    # #pylint: disable=too-many-instance-attributes

    def __init__(self, config: Config, bucket_config: S3BucketConfig):
        self.name: str = ""
        self.public: bool = False
        self.tags: list = []
        self.region: str = "us-east-1"
        self.sigv4: bool = True
        self._bucket_config = bucket_config
        self._config: Config = config
        self._client = bucket_config.client
        self._acl = ""
        self._policy = None
        self._created = False
        self.s3_session = self._client.get("s3", region=self.region)
        self._determine_name()
        if self._bucket_config.region:
            self.region = self._bucket_config.region
        # Account
        self.account = self._bucket_config.account
        # Client
        if self._bucket_config.client:
            self._client = self._bucket_config.client
        self._determine_bucket_attributes()

    def _determine_name(self):
        # Name
        if self._config.s3_bucket.name:
            self._assert_bucket_exists(self._config.s3_bucket.name)
            self.name = self._config.s3_bucket.name
            self._created = True

        if self._bucket_config.name:
            self.name = self._bucket_config.name

    def _determine_bucket_attributes(self):
        self.sigv4 = not self._config.enable_sig_v2
        self.tags = self._config.tags
        self.public = self._config.s3_bucket.public

    @property
    def acl(self):
        return self._acl

    @property
    def policy(self):
        return self._policy

    @property
    def client(self):
        return self._client

    @property
    def sigv4_policy(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Test",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": f"arn:aws:s3:::{self.name}/*",
                    "Condition": {"StringEquals": {"s3:signatureversion": "AWS"}},
                }
            ],
        }
        return json.dumps(policy)

    def _create_in_region(self):
        if self.region == "us-east-1":
            response = self.s3_session.create_bucket(ACL=self.acl, Bucket=self.name)
        else:
            response = self.s3_session.create_bucket(
                ACL=self.acl,
                Bucket=self.name,
                CreateBucketConfiguration={"LocationConstraint": self.region},
            )

        return S3APIResponse(response)

    def _create_bucket(self, bucket_name):
        _create_resp = self._create_in_region()
        if _create_resp.ok:
            LOG.info(f"Staging Bucket: [{bucket_name}]")

        if self.tags:
            LOG.info(f"Propagating tags to this bucket.")
            self.s3_session.put_bucket_tagging(
                Bucket=bucket_name, Tagging={"TagSet": self.tags}
            )

        if self.sigv4:
            LOG.info(f"Enforcing SigV4 requests for bucket ${bucket_name}")
            self.s3_session.put_bucket_policy(
                Bucket=self.name, Policy=self.sigv4_policy
            )

    def _assert_bucket_exists(self, name):

        # Verify bucket exists.
        try:
            _ = self.s3_session.list_objects(Bucket=name)
        except self.s3_session.exceptions.NoSuchBucket:
            raise TaskCatException(
                f"The bucket you provided ({name}) does " f"not exist. Exiting."
            )
        return True

    def create(self):
        if self._created:
            return

        # Verify bucket name length
        if len(self.name) > self._config.s3_bucket.max_name_len:
            raise S3BucketCreatorException(
                f"The bucket name you provided [{self._config.s3_bucket.name}] \
                is greater than {self._config.s3_bucket.max_name_len} characters."
            )

        LOG.info(f"Creating bucket in {self.region} for account {self.account}")
        self._create_bucket(self.name)
        self._created = True


def stage_in_s3(config: Config):
    """
    Upload templates and other artifacts to s3.

    This function creates the s3 bucket with name provided in the config yml file. If
    no bucket name provided, it creates the s3 bucket using project name provided in
    config yml file. And uploads the templates and other artifacts to the s3 bucket.

    :param config: Taskcat config object.

    """
    bucket_cache: dict = {}

    # Create the bucket objects first!
    for test in config.tests.values():
        for region in test.regions:
            cached_bucket = bucket_cache.get(
                f"{region.client.account}_{region.s3bucket.name}", None
            )
            if cached_bucket:
                region.s3bucket = cached_bucket
            else:
                region.s3bucket = S3BucketCreator(config, region.s3bucket)
                bucket_cache[
                    f"{region.client.account}_{region.s3bucket.name}"
                ] = region.s3bucket

    # Sync!
    for bucket in bucket_cache.values():
        try:
            bucket.create()
        except Exception as e:
            raise TaskCatException(e)
    for bucket in bucket_cache.values():
        S3Sync(
            bucket.s3_session, bucket.name, config.name, config.project_root, bucket.acl
        )


# pylint: disable=line-too-long
# self.s3_url_prefix = "https://" + self.get_s3_hostname() + "/" + self.get_project_name()
