#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function

import hashlib
import fnmatch
import os
import time
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool
from taskcat.colored_console import PrintMsg
from boto3.exceptions import S3UploadFailedError
from taskcat.exceptions import TaskCatException


class S3Sync(object):
    """Syncronizes local project files with S3 based on checksums.

    Excludes hidden files, unpackaged lambda source and taskcat /ci/ files.
    Uses the Etag as an md5 which introduces the following limitations
        * Uses undocumented etag algorithm for multipart uploads
        * Does not work wil files uploaded in the console that use SSE encryption
        * see https://docs.aws.amazon.com/AmazonS3/latest/API/RESTCommonResponseHeaders.html for more info
    Does not support buckets with versioning enabled
    """

    exclude_files = [
        ".*",
        "*.md"
    ]
    exclude_path_prefixes = [
        "functions/source/",
        "."
    ]

    exclude_remote_path_prefixes = []

    def __init__(self, s3_client, bucket, prefix, path, acl="private"):
        """Syncronizes local file system with an s3 bucket/prefix

        """
        if prefix != "" and not prefix.endswith('/'):
            prefix = prefix + '/'
        self.s3_client = s3_client
        fl = self._get_local_file_list(path)
        s3fl = self._get_s3_file_list(bucket, prefix)
        self._sync(fl, s3fl, bucket, prefix, acl=acl)
        return

    def _hash_file(self, file_path, chunk_size=8 * 1024 * 1024):
        # This is a bit funky because of the way multipart upload etags are done, they are a md5 of the md5's from each part with the number of parts appended
        # credit to hyperknot https://github.com/aws/aws-cli/issues/2585#issue-226758933
        md5s = []

        with open(file_path, 'rb') as fp:
            while True:
                data = fp.read(chunk_size)
                if not data:
                    break
                md5s.append(hashlib.md5(data))

        if len(md5s) == 1:
            return '"{}"'.format(md5s[0].hexdigest())

        digests = b''.join(m.digest() for m in md5s)
        digests_md5 = hashlib.md5(digests)
        return '"{}-{}"'.format(digests_md5.hexdigest(), len(md5s))

    def _get_local_file_list(self, path, include_checksums=True):
        file_list = {}
        # get absolute local path
        path = os.path.abspath(os.path.expanduser(path))
        # recurse through directories
        for root, dirs, files in os.walk(path):
            relpath = os.path.relpath(root, path) + "/"
            exclude_path = False
            # relative path should be blank if there are no sub directories
            if relpath == './':
                relpath = ""
            # exclude defined paths
            for p in S3Sync.exclude_path_prefixes:
                if relpath.startswith(p):
                    exclude_path = True
                    break
            if not exclude_path:
                for file in files:
                    exclude = False
                    # exclude defined filename patterns
                    for p in S3Sync.exclude_files:
                        if fnmatch.fnmatch(file, p):
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
            # this is a query to get additional pages, add continuation token to get next page
            else:
                resp = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, ContinuationToken=continuation_token)
            if 'Contents' in resp:
                for file in resp['Contents']:
                    # strip the prefix from the path
                    relpath = file['Key'][len(prefix):]
                    objects[relpath] = file['ETag']
            if 'NextContinuationToken' in resp.keys():
                continuation_token = resp['NextContinuationToken']
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

    def _sync(self, local_list, s3_list, bucket, prefix, acl, threads=16):
        # determine which files to remove from S3
        remove_from_s3 = []
        for s3_file in s3_list.keys():
            if s3_file not in local_list.keys() and not self._exclude_remote(s3_file):
                print("{}[S3: DELETE ]{} s3://{}/{}".format(PrintMsg.white, PrintMsg.rst_color, bucket, prefix + prefix + s3_file))
                remove_from_s3.append({"Key": prefix + s3_file})
        # deleting objects, max 1k objects per s3 delete_objects call
        for d in [remove_from_s3[i:i + 1000] for i in range(0, len(remove_from_s3), 1000)]:
            response = self.s3_client.delete_objects(Bucket=bucket, Delete={'Objects': d})
            if "Errors" in response.keys():
                for error in response["Errors"]:
                    print(PrintMsg.ERROR + "S3 delete error: %s" % str(error))
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
        func = partial(self._s3_upload_file, prefix=prefix, s3_client=self.s3_client, acl=acl)
        pool.map(func, upload_to_s3)
        pool.close()
        pool.join()

    def _s3_upload_file(self, paths, prefix, s3_client, acl):
        local_filename, bucket, s3_path = paths
        retry = 0
        # backoff and retry
        while retry < 5:
            print("{}[S3: -> ]{} s3://{}/{}".format(PrintMsg.white, PrintMsg.rst_color, bucket, prefix + s3_path))
            try:
                s3_client.upload_file(local_filename, bucket, prefix + s3_path, ExtraArgs={'ACL': acl})
                break
            except Exception as e:
                retry += 1
                print(PrintMsg.ERROR + "S3 upload error: %s" % e)
                # give up if we've exhausted retries, or if the error is not-retryable (ie AccessDenied)
                if retry == 5 or (type(e) == S3UploadFailedError and '(AccessDenied)' in str(e)):
                    raise TaskCatException("Failed to upload to S3")
                time.sleep(retry * 2)
