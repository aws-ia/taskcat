import logging

from uuid import uuid4
from taskcat.exceptions import TaskCatException
from taskcat.config import Config
from taskcat.s3_sync import S3Sync
from taskcat.client_factory import ClientFactory

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

    SIGV4_POLICY = """{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Test",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": "arn:aws:s3:::{bucket}/*",
                    "Condition": {
                         "StringEquals": {
                               "s3:signatureversion": "AWS"
                         }
                    }
                }
            ]
        }"""

    def __init__(self, config: Config):
        self.name: str = ""
        self.public: bool = False
        self.tags: list = []
        self.region: str = "us-east-1"
        self.sigv4: bool = True
        self._config: Config = config
        self._client = None
        self._acl = None
        self._policy = None

        if config.s3_bucket.name:
            self.name = config.s3_bucket.name

        if config.s3_bucket.public:
            self.public = True

        if config.s3_bucket.tags:
            self.tags = config.s3_bucket.tags

        if config.s3_bucket.region != "us-east-1":
            self.region = config.s3_bucket.region

        self.sigv4 = not config.enable_sig_v2

    @property
    def acl(self):
        return self._acl

    @property
    def policy(self):
        return self._policy

    @property
    def client(self):
        return self._client

    def _create_in_region(self):
        if self.region == "us-east-1":
            response = self._client.create_bucket(ACL=self.acl, Bucket=self.name)
        else:
            response = self._client.create_bucket(
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
            self._client.put_bucket_tagging(
                Bucket=bucket_name, Tagging={"TagSet": self.tags}
            )

        if self.sigv4:
            LOG.info(f"Enforcing sigv4 requests for bucket ${bucket_name}")
            policy = self.SIGV4_POLICY.format(bucket=self.name)
            self._client.put_bucket_policy(Bucket=self.name, Policy=policy)

    def _assert_bucket_exists(self):
        if not self._config.s3_bucket.name:

            # Verify bucket exists.
            try:
                _ = self._client.list_objects(Bucket=self.name)
            except self._client.exceptions.NoSuchBucket:
                raise TaskCatException(
                    f"The bucket you provided ({self.name}) does "
                    f"not exist. Exiting."
                )
        return True

    def create(self):
        # Verify bucket name length
        if len(self.name) > self._config.s3_bucket.max_name_len:
            raise S3BucketCreatorException(
                f"The bucket you provided [{self._config.s3_bucket.name}] is greater "
                f"than {self._config.s3_bucket.max_name_len} characters."
            )
        # TODO: need to get a client from an appropriate already existing client_factory
        # TODO: address potential of multiple buckets
        self._client = ClientFactory().get(
            "s3", region=self._config.s3_bucket.name, s3v4=self.sigv4
        )

        if self._config.s3_bucket.name:
            self._assert_bucket_exists()
            self.name = self._config.s3_bucket.name
            return

        auto_bucket_name = (
            f"taskcat-{self._config.stack_prefix}-{self.name}-"
            f"{uuid4()}".lower()[:63]
        )
        LOG.info(f"Creating bucket {auto_bucket_name} in {self.region}")
        self._create_bucket(auto_bucket_name)
        self._config.s3_bucket.auto = True
        self.name = auto_bucket_name


def stage_in_s3(config: Config):
    """
    Upload templates and other artifacts to s3.

    This function creates the s3 bucket with name provided in the config yml file. If
    no bucket name provided, it creates the s3 bucket using project name provided in
    config yml file. And uploads the templates and other artifacts to the s3 bucket.

    :param config: Taskcat config object.

    """
    s3_bucket = S3BucketCreator(config)

    try:
        s3_bucket.create()
    except Exception as e:
        raise TaskCatException(e)

    S3Sync(
        s3_bucket.client,
        s3_bucket.name,
        config.name,
        str(config.project_root),
        s3_bucket.acl,
    )
