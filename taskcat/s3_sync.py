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


class S3Sync(object):
    """Syncronizes local project files with S3 based on checksums.

    Excludes hidden files, unpackaged lambda source and taskcat /ci/ files.
    Uses the Etag as an md5 which introduces the following limitations
        * Uses undocumented etag algorithm for multipart uploads
        * Does not work wil files uploaded in the console that use SSE encryption
        * see https://docs.aws.amazon.com/AmazonS3/latest/API/RESTCommonResponseHeaders.html for more info
    Does not support buckets with versioning enabled
    """

    _exclude_files = [
        ".*",
        "*.md"
    ]
    _exclude_path_prefixes = [
        "functions/source/",
        ".",
        "ci/"
    ]

    def __init__(self, s3_client, bucket, prefix, path, acl=None):
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
        file_list = []
        path = os.path.abspath(os.path.expanduser(path))
        for root, dirs, files in os.walk(path):
            relpath = os.path.relpath(root, path) + "/"
            exclude_path = False
            if relpath == './':
                relpath = ""
            for p in S3Sync._exclude_path_prefixes:
                if relpath.startswith(p):
                    exclude_path = True
                    break
            if not exclude_path:
                for file in files:
                    exclude = False
                    for p in S3Sync._exclude_files:
                        if fnmatch.fnmatch(file, p):
                            exclude = True
                            break
                    if not exclude:
                        full_path = root + "/" + file
                        if include_checksums:
                            checksum = self._hash_file(full_path)
                        else:
                            checksum = ""
                        file_list.append([full_path, relpath + file, checksum])
        return file_list

    def _get_s3_file_list(self, bucket, prefix):
        objects = []
        more_objects = True
        continuation_token = None
        while more_objects:
            if not continuation_token:
                resp = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            else:
                resp = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, ContinuationToken=continuation_token)
            if 'Contents' in resp:
                objects += [[i['Key'][len(prefix):], i['ETag']] for i in resp['Contents']]
            if 'NextContinuationToken' in resp.keys():
                continuation_token = resp['NextContinuationToken']
            else:
                more_objects = False
        return objects

    def _sync(self, local_list, s3_list, bucket, prefix, acl, threads=16):
        # determine which files to remove from S3
        remove_from_s3 = []
        for s3f in s3_list:
            remove = True
            for f in local_list:
                if s3f[0] == f[1]:
                    remove = False
                    break
            if remove:
                remove_from_s3.append({"Key": prefix + s3f[0]})
        # deleting objects, max 1k objects per s3 delete_objects call
        for d in [remove_from_s3[i:i + 1000] for i in range(0, len(remove_from_s3), 1000)]:
            self.s3_client.delete_objects(Bucket=bucket, Delete={'Objects': d})
        # build list of files to upload
        upload_to_s3 = []
        for f in local_list:
            upload = True
            for s3f in s3_list:
                if s3f[0] == f[1] and s3f[1] == f[2]:
                    upload = False
            if upload:
                upload_to_s3.append([f[0], bucket, f[1]])
        pool = ThreadPool(threads)
        func = partial(self._s3_upload_file, prefix=prefix, s3_client=self.s3_client, acl=acl)
        pool.map(func, upload_to_s3)
        pool.close()
        pool.join()

    def _s3_upload_file(self, paths, prefix, s3_client, acl):
        local_filename, bucket, s3_path = paths
        retry = 0
        while retry < 5:
            try:
                s3_client.upload_file(local_filename, bucket, prefix + s3_path, ExtraArgs={'ACL': acl})
                print("{}[S3: -> ]{} s3://{}/{}".format(PrintMsg.white, PrintMsg.rst_color, bucket, prefix + s3_path))
                break
            except Exception as e:
                retry += 1
                time.sleep(retry * 2)
                print(PrintMsg.ERROR + "S3 upload error: %s" % e)
