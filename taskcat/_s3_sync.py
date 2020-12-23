import fnmatch
import hashlib
import logging
import os
import time
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool
from typing import List

from boto3.exceptions import S3UploadFailedError
from boto3.s3.transfer import TransferConfig

from taskcat._logger import PrintMsg
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class S3Sync:
    """Syncronizes local project files with S3 based on checksums.

    Excludes hidden files, unpackaged lambda source and taskcat /ci/ files.
    Uses the Etag as an md5 which introduces the following limitations
        * Uses undocumented etag algorithm for multipart uploads
        * Does not work wil files uploaded in the console that use SSE encryption
        * see
          https://docs.aws.amazon.com/AmazonS3/latest/API/RESTCommonResponseHeaders.html
          for more info
    Does not support buckets with versioning enabled
    """

    # TODO: better exclusions that support path wildcards, eg. "*/.git/*"
    exclude_files = [".*", "*.md"]
    exclude_path_prefixes = [
        "lambda_functions/source/",
        "functions/source/",
        ".",
        "venv/",
        "taskcat_outputs/",
    ]

    exclude_remote_path_prefixes: List[str] = []

    def __init__(self, s3_client, bucket, prefix, path, acl="private", dry_run=False):
        """Syncronizes local file system with an s3 bucket/prefix

        """
        if prefix != "" and not prefix.endswith("/"):
            prefix = prefix + "/"
        self.s3_client = s3_client
        self.dry_run = dry_run
        file_list = self._get_local_file_list(path)
        s3_file_list = self._get_s3_file_list(bucket, prefix)
        self._sync(file_list, s3_file_list, bucket, prefix, acl=acl)

    @staticmethod
    def _hash_file(file_path, chunk_size=8 * 1024 * 1024):
        # This is a bit funky because of the way multipart upload etags are done, they
        # are a md5 of the md5's from each part with the number of parts appended
        # credit to hyperknot https://github.com/aws/aws-cli/issues/2585#issue-226758933
        md5s = []

        with open(file_path, "rb") as file_handle:
            while True:
                data = file_handle.read(chunk_size)
                if not data:
                    break
                md5s.append(hashlib.md5(data))  # nosec

        if len(md5s) == 1:
            return '"{}"'.format(md5s[0].hexdigest())

        digests = b"".join(m.digest() for m in md5s)
        digests_md5 = hashlib.md5(digests)  # nosec
        return '"{}-{}"'.format(digests_md5.hexdigest(), len(md5s))

    # TODO: refactor
    def _get_local_file_list(
        self, path, include_checksums=True
    ):  # pylint: disable=too-many-locals
        file_list = {}
        # get absolute local path
        path = os.path.abspath(os.path.expanduser(path))
        # recurse through directories
        for root, _, files in os.walk(path):
            relpath = os.path.relpath(root, path) + "/"
            exclude_path = False
            # relative path should be blank if there are no sub directories
            if relpath == "./":
                relpath = ""
            # exclude defined paths
            for prefix in S3Sync.exclude_path_prefixes:
                if relpath.startswith(prefix):
                    exclude_path = True
                    break
            if not exclude_path:
                file_list.update(
                    self._iterate_files(files, root, include_checksums, relpath)
                )
        return file_list

    def _iterate_files(self, files, root, include_checksums, relpath):
        file_list = {}
        for file in files:
            exclude = False
            # exclude defined filename patterns
            for pattern in S3Sync.exclude_files:
                if fnmatch.fnmatch(file, pattern):
                    exclude = True
                    break
            if not exclude:
                full_path = root + "/" + file
                if include_checksums:
                    # get checksum
                    checksum = self._hash_file(full_path)
                else:
                    checksum = ""
                file_list[relpath + file] = [full_path, checksum]
        return file_list

    def _get_s3_file_list(self, bucket, prefix):
        objects = {}
        is_paginated = True
        continuation_token = None
        # While there are more results, fetch them from S3
        while is_paginated:
            # if there's no token, this is the initial list_objects call
            if not continuation_token:
                resp = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            # this is a query to get additional pages, add continuation token to get
            # next page
            else:
                resp = self.s3_client.list_objects_v2(
                    Bucket=bucket, Prefix=prefix, ContinuationToken=continuation_token
                )
            if "Contents" in resp:
                for file in resp["Contents"]:
                    # strip the prefix from the path
                    relpath = file["Key"][len(prefix) :]
                    objects[relpath] = file["ETag"]
            if "NextContinuationToken" in resp.keys():
                continuation_token = resp["NextContinuationToken"]
            # If there's no toke in the response we've fetched all the objects
            else:
                is_paginated = False
        return objects

    @staticmethod
    def _exclude_remote(path):
        keep = False
        for exclude in S3Sync.exclude_remote_path_prefixes:
            if path.startswith(exclude):
                keep = True
                break
        return keep

    # TODO: refactor
    def _sync(  # noqa: C901
        self, local_list, s3_list, bucket, prefix, acl, threads=16
    ):  # pylint: disable=too-many-locals
        # determine which files to remove from S3
        remove_from_s3 = []
        for s3_file in s3_list.keys():
            if s3_file not in local_list.keys() and not self._exclude_remote(s3_file):
                if self.dry_run:
                    LOG.info(
                        f"[DRY RUN] s3://{bucket}/{prefix + prefix + s3_file}",
                        extra={"nametag": PrintMsg.S3DELETE},
                    )
                else:
                    LOG.info(
                        f"s3://{bucket}/{prefix + prefix + s3_file}",
                        extra={"nametag": PrintMsg.S3DELETE},
                    )
                remove_from_s3.append({"Key": prefix + s3_file})
        # deleting objects, max 1k objects per s3 delete_objects call
        if not self.dry_run:
            for objects in [
                remove_from_s3[i : i + 1000]
                for i in range(0, len(remove_from_s3), 1000)
            ]:
                response = self.s3_client.delete_objects(
                    Bucket=bucket, Delete={"Objects": objects}
                )
                if "Errors" in response.keys():
                    for error in response["Errors"]:
                        LOG.error("S3 delete error: %s" % str(error))
                    raise TaskCatException("Failed to delete one or more files from S3")
        # build list of files to upload
        upload_to_s3 = []
        for local_file in local_list:
            upload = False
            # If file is not present in S3
            if local_file not in s3_list.keys():
                upload = True
            # If checksum is different
            elif local_list[local_file][1] != s3_list[local_file]:
                upload = True
            if upload:
                absolute_path = local_list[local_file][0]
                s3_path = local_file
                upload_to_s3.append([absolute_path, bucket, s3_path])
        # multithread the uploading of files
        pool = ThreadPool(threads)
        func = partial(
            self._s3_upload_file, prefix=prefix, s3_client=self.s3_client, acl=acl
        )
        pool.map(func, upload_to_s3)
        pool.close()
        pool.join()

    def _s3_upload_file(self, paths, prefix, s3_client, acl):
        local_filename, bucket, s3_path = paths
        retry = 0
        # backoff and retry
        while retry < 5:
            if self.dry_run:
                LOG.info(
                    f"[DRY_RUN] s3://{bucket}/{prefix + s3_path}",
                    extra={"nametag": PrintMsg.S3},
                )
                break
            LOG.info(
                f"s3://{bucket}/{prefix + s3_path}", extra={"nametag": PrintMsg.S3}
            )
            try:
                s3_client.upload_file(
                    local_filename,
                    bucket,
                    prefix + s3_path,
                    ExtraArgs={"ACL": acl},
                    Config=TransferConfig(use_threads=False),
                )
                break
            except Exception as e:  # pylint: disable=broad-except
                retry += 1
                LOG.error("S3 upload error: %s" % e)
                # give up if we've exhausted retries, or if the error is not-retryable
                # ie. AccessDenied
                if retry == 5 or (
                    isinstance(e, S3UploadFailedError) and "(AccessDenied)" in str(e)
                ):
                    # pylint: disable=raise-missing-from
                    raise TaskCatException("Failed to upload to S3")
                time.sleep(retry * 2)
