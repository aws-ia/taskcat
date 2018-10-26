#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function

import json
import argparse
import os
import shutil
import hashlib
import datetime
import logging
import sys
from collections import OrderedDict
from taskcat.client_factory import ClientFactory
from taskcat.utils import CFNYAMLHandler
from taskcat.exceptions import TaskCatException

class CFNAlchemist(object):
    OBJECT_REWRITE_MODE = 10
    BASIC_REWRITE_MODE = 20

    def __init__(
        self,
        input_path,
        target_bucket_name,
        source_bucket_name=None,
        target_key_prefix=None,
        source_key_prefix=None,
        output_directory=None,
        rewrite_mode=OBJECT_REWRITE_MODE,
        verbose=False,
        dry_run=False
    ):
        """
        Construct an Alchemist object.

        :param input_path: Directory path to the root of the assets
        :param target_bucket_name: Target S3 bucket to use as replacement and to upload to
        :param source_bucket_name: Source S3 bucket to search for replacement
        :param target_key_prefix: Target S3 key prefix to prepend to all object (including an ending forward slash '/')
        :param output_directory: Directory to save rewritten assets to
        :param rewrite_mode: Mode for rewriting like CFNAlchemist.OBJECT_REWRITE_MODE or CFNAlchemist.BASIC_REWRITE_MODE
        :param verbose: Set to True to log debug messages
        :param dry_run: Set to True to perform a dry run
        """
        # create logger
        self.logger = logging.getLogger('alchemist')
        self.logger.setLevel(logging.INFO)
        # create console handler and set level to debug
        self.ch = logging.StreamHandler()
        self.ch.setLevel(logging.INFO)
        # create formatter
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # add formatter to ch
        self.ch.setFormatter(self.formatter)
        # add ch to logger
        self.logger.addHandler(self.ch)

        # Constants
        self._TEMPLATE_EXT = ['.template', '.json', '.yaml', '.yml']
        self._GIT_EXT = ['.git', '.gitmodules', '.gitignore', '.gitattributes']
        self._EXCLUDED_DIRS = ['.git', 'ci', '.idea', '.vs']

        # properties
        self._boto_clients = ClientFactory(logger=self.logger)
        self._auth_mode = None
        self._aws_profile = None
        self._aws_access_key_id = None
        self._aws_secret_access_key = None
        self._aws_session_token = None

        # properties with setters/getters
        self._input_path = None
        self._target_bucket_name = None
        self._target_key_prefix = None
        self._output_directory = None
        self._rewrite_mode = self.OBJECT_REWRITE_MODE
        self._excluded_prefixes = None
        self._verbose = False
        self._dry_run = False
        self._prod_bucket_name = 'aws-quickstart'
        self._prod_key_prefix = None
        self._default_region = 'us-east-1'
        self._file_list = None

        # initialize
        self.set_input_path(input_path)
        self.set_prod_bucket_name(source_bucket_name)
        self.set_target_bucket_name(target_bucket_name)
        self.set_target_key_prefix(target_key_prefix)
        self.set_output_directory(output_directory)
        if rewrite_mode not in [self.OBJECT_REWRITE_MODE, self.BASIC_REWRITE_MODE]:
            self.logger.error("Invalid rewrite_mode.")
        else:
            self.set_rewrite_mode(rewrite_mode)
        self.set_verbose(verbose)
        self.set_dry_run(dry_run)
        self.set_prod_key_prefix(source_key_prefix)

        return

    def set_verbose(self, verbose):
        self._verbose = verbose
        self.logger.setLevel(logging.DEBUG if self._verbose else logging.INFO)
        self.ch.setLevel(logging.DEBUG if self._verbose else logging.INFO)

    def get_verbose(self):
        return self._verbose

    def set_dry_run(self, dry_run):
        self._dry_run = dry_run

    def get_dry_run(self):
        return self._dry_run

    def set_input_path(self, input_path):
        self._input_path = input_path

    def get_input_path(self):
        return self._input_path

    def set_prod_key_prefix(self, source_key_prefix):
        if source_key_prefix is not None:
            self._prod_key_prefix = source_key_prefix.strip('/') + '/'

    def get_prod_key_prefix(self):
        return self._prod_key_prefix

    def set_target_bucket_name(self, target_bucket_name):
        self._target_bucket_name = target_bucket_name

    def get_target_bucket_name(self):
        return self._target_bucket_name

    def set_target_key_prefix(self, target_key_prefix):
        if target_key_prefix is not None:
            self._target_key_prefix = target_key_prefix.strip('/') + '/'
            self._set_excluded_key_prefixes()

    def get_target_key_prefix(self):
        return self._target_key_prefix

    def set_output_directory(self, output_directory):
        self._output_directory = output_directory

    def get_output_directory(self):
        return self._output_directory

    def set_rewrite_mode(self, rewrite_type):
        self._rewrite_mode = rewrite_type

    def get_rewrite_mode(self):
        return self._rewrite_mode

    def set_prod_bucket_name(self, prod_bucket_name):
        if prod_bucket_name is not None:
            self._prod_bucket_name = prod_bucket_name

    def get_prod_bucket_name(self):
        return self._prod_bucket_name

    def set_default_region(self, region):
        self._default_region = region

    def get_default_region(self):
        return self._default_region

    def _set_excluded_key_prefixes(self):
        self._excluded_prefixes = [
            '{}doc/'.format(self._target_key_prefix),
            '{}pics/'.format(self._target_key_prefix),
            '{}media/'.format(self._target_key_prefix),
            '{}downloads/'.format(self._target_key_prefix),
            '{}installers/'.format(self._target_key_prefix)
        ]

    def _get_excluded_key_prefixes(self):
        return self._excluded_prefixes

    def upload_only(self):
        """
        This function uploads all assets to the target S3 bucket name using the target S3 key prefix for each object.
          A comparison of checksums is done for all object as well to avoid reuploading files that have not changed (this
          checksum comparison is only effective on non-multi part uploaded files).
        """
        if self._target_key_prefix is None:
            raise TaskCatException('target_key_prefix cannot be None')
        # TODO: FIGURE OUT BOTO SESSION HANDLING DETAILS CURRENTLY USING ClientFactory's get_session from utils.py
        '''
        # Use a profile
        if args.profile:
            boto_session = boto3.Session(profile_name=args.profile)
            s3_resource = boto_session.resource('s3')
        # Use explicit credentials
        elif args.access_key_id and args.secret_access_key:
            boto_session = boto3.Session(aws_access_key_id=args.access_key_id,
                                         aws_secret_access_key=args.secret_access_key)
            s3_resource = boto_session.resource('s3')
        # Attempt to use IAM role from instance profile
        else:
            boto_session = boto3.Session()
            s3_resource = boto_session.resource('s3')
        '''
        boto_session = self._boto_clients.get_session(
            credential_set='alchemist',
            region=self.get_default_region()
        )
        s3_resource = boto_session.resource('s3')
        upload_bucket = s3_resource.Bucket(self._target_bucket_name)

        self.logger.info("Gathering remote S3 bucket keys {}*".format(self._target_key_prefix))
        remote_key_dict = {}
        for obj in upload_bucket.objects.filter(Prefix='{}'.format(self._target_key_prefix)):
            if any(x not in obj.key for x in self._get_excluded_key_prefixes()):
                remote_key_dict[obj.key] = obj
        self.logger.debug(remote_key_dict.keys())

        # Gather file list
        # NOTE: We only use the output directory if it's been set (that is, a rewrite was expected to have happened to
        #       an output directory. We ensure that is not the case when parsing the args, but care must be taken
        #       when initializing all the properties of this class. If it's only an upload that's meant to happen
        #       without a previous rewrite, then output directory should never be set.
        self.logger.info("Gathering local keys {}*".format(self._target_key_prefix))
        if self._file_list:
            file_list = self._file_list
        else:
            file_list = self._get_file_list(self._input_path)

        local_key_dict = {}
        for current_file in file_list:
            local_key_dict[os.path.join(self._target_key_prefix, current_file.replace(self._input_path, '', 1).lstrip('\/')).replace('\\', '/')] = \
                os.path.join(self._output_directory if self._output_directory and not self._dry_run else self._input_path, current_file.replace(self._input_path, '', 1).lstrip('\/'))
        self.logger.debug(local_key_dict.keys())

        remote_to_local_diff = list(set(remote_key_dict.keys()) - set(local_key_dict.keys()))
        self.logger.info("Keys in remote S3 bucket but not in local:")
        self.logger.info(remote_to_local_diff)

        local_to_remote_diff = list(set(local_key_dict.keys()) - set(remote_key_dict.keys()))
        self.logger.info("Keys in local but not in remote S3 bucket:")
        self.logger.info(local_to_remote_diff)

        self.logger.info("Syncing objects to S3 bucket [{}]".format(self._target_bucket_name))
        for _key in local_key_dict.keys():
            if _key in remote_key_dict:
                self.logger.debug("File [{0}] exists in S3 bucket [{1}]. Verifying MD5 checksum for difference.".format(_key, self._target_bucket_name))
                s3_hash = remote_key_dict[_key].e_tag.strip('"')
                local_hash = hashlib.md5(open(local_key_dict[_key], 'rb').read()).hexdigest()
                self.logger.debug("S3 MD5 checksum (etag) [{0}]=>[{1}]".format(s3_hash, remote_key_dict[_key]))
                self.logger.debug("Local MD5 checksum     [{0}]=>[{1}]".format(local_hash, local_key_dict[_key]))
                if s3_hash != local_hash:
                    if self._dry_run:
                        self.logger.info("[WHAT IF DRY RUN]: UPDATE [{0}]".format(_key))
                    else:
                        self.logger.info("UPDATE [{0}]".format(_key))
                        s3_resource.Object(self._target_bucket_name, _key).upload_file(local_key_dict[_key])
                else:
                    self.logger.debug("MD5 checksums are the same. Skipping [{}]".format(_key))
            else:
                if self._dry_run:
                    self.logger.info("[WHAT IF DRY RUN]: CREATE [{0}]".format(_key))
                else:
                    self.logger.info("CREATE [{0}]".format(_key))
                    # Upload local file not present in S3 bucket
                    s3_resource.Object(self._target_bucket_name, _key).upload_file(local_key_dict[_key])

        # clean up/remove remote keys that are not in local keys
        for _key in remote_to_local_diff:
            if not any(x in _key for x in self._get_excluded_key_prefixes()):
                if self._dry_run:
                    self.logger.info("[WHAT IF DRY RUN]: DELETE [{0}]".format(_key))
                else:
                    self.logger.info("DELETE [{0}]".format(_key))
                    remote_key_dict[_key].delete()

    def rewrite_only(self):
        """
        This function searches through all the files and rewrites any references of the production S3 bucket name
         to the target S3 bucket name. This is done by both things like line-by-line basic rewrites or walking the
         tree of a JSON or YAML document to find the references.
        """
        # Create file list and recurse if args._input_path is directory
        file_list = self._get_file_list(self._input_path)
        self.logger.info("Files to be worked on:")
        self.logger.info(file_list)

        # Validate output
        if self._output_directory is not None:
            CFNYAMLHandler.validate_output_dir(self._output_directory)

        self.logger.info("Production S3 bucket name that we are looking for [{}]".format(self._prod_bucket_name))
        self.logger.info("Replacement S3 bucket name that we are rewriting with [{}]".format(self._target_bucket_name))
        self.logger.info("Production S3 key prefix that we are looking for [{}]".format(self._prod_key_prefix))
        self.logger.info("Replacement S3 key prefix that we are rewriting with [{}]".format(self._target_key_prefix))

        # Rewrite files
        for current_file in file_list:
            # Determine output file
            if self._output_directory:
                if len(file_list) == 1:
                    output_file = os.path.join(self._output_directory, os.path.basename(current_file))
                else:
                    output_file = os.path.join(self._output_directory, current_file.replace(self._input_path, '', 1).lstrip('\/'))
            else:
                output_file = current_file

            # Load current file
            if self._rewrite_mode != self.BASIC_REWRITE_MODE \
                    and current_file.endswith(tuple(self._TEMPLATE_EXT)) \
                    and os.path.dirname(current_file).endswith('/templates'):
                self.logger.info("Opening file [{}]".format(current_file))
                with open(current_file, 'r', newline=None) as template:
                    template_raw_data = template.read()
                    template.close()
                template_raw_data = template_raw_data.strip()

                if template_raw_data[0] in ['{', '['] and template_raw_data[-1] in ['}', ']']:
                    self.logger.info('Detected JSON. Loading file.')
                    FILE_FORMAT = 'JSON'
                    template_data = json.load(open(current_file, 'r', newline=None), object_pairs_hook=OrderedDict)
                else:
                    self.logger.info('Detected YAML. Loading file.')
                    FILE_FORMAT = 'YAML'
                    template_data = CFNYAMLHandler.ordered_safe_load(open(current_file, 'r', newline=None), object_pairs_hook=OrderedDict)

                if FILE_FORMAT in ['JSON', 'YAML']:
                    # Iterate through every top level node.
                    # This was only added in case we need to examine only parts of the template
                    if type(template_data) in [OrderedDict, dict]:
                        for node_key in template_data.keys():
                            self.logger.debug("Working on node [{}]".format(node_key))
                            self._recurse_nodes(template_data[node_key])
                    elif type(template_data) is list:
                        self._recurse_nodes(template_data)
                    else:
                        if self._dry_run:
                            self.logger.warning("[WHAT IF DRY RUN]: [{0}] Unsupported {1} structure. Skipping but copying.".format(current_file, FILE_FORMAT))
                        else:
                            self.logger.warning("[{0}] Unsupported {1} structure. Skipping but copying.".format(current_file, FILE_FORMAT))
                            if current_file is not output_file:
                                shutil.copyfile(current_file, output_file)

                    # Write modified template
                    if self._dry_run:
                        self.logger.info("[WHAT IF DRY RUN]: Writing file [{}]".format(output_file))
                    else:
                        self.logger.info("Writing file [{}]".format(output_file))
                        CFNYAMLHandler.validate_output_dir(os.path.split(output_file)[0])
                        with open(output_file, 'w') as updated_template:
                            if FILE_FORMAT == 'JSON':
                                updated_template.write(json.dumps(template_data, indent=4, separators=(',', ': ')))
                            elif FILE_FORMAT == 'YAML':
                                updated_template.write(
                                    CFNYAMLHandler.ordered_safe_dump(template_data, indent=2, allow_unicode=True, default_flow_style=False, explicit_start=True, explicit_end=True))
                        updated_template.close()
                else:
                    if self._dry_run:
                        self.logger.warning("[WHAT IF DRY RUN]: [{}] Unsupported file format. Skipping but copying.".format(current_file))
                    else:
                        self.logger.warning("[{}] Unsupported file format. Skipping but copying.".format(current_file))
                        if current_file is not output_file:
                            shutil.copyfile(current_file, output_file)
            else:
                self.logger.info("Opening file [{}]".format(current_file))
                try:
                    with open(current_file, 'r', newline=None) as f:
                        file_data = f.readlines()

                    for index, line in enumerate(file_data):
                        file_data[index] = self._string_rewriter(line)

                    # Write modified file
                    if self._dry_run:
                        self.logger.info("[WHAT IF DRY RUN]: Writing file [{}]".format(output_file))
                    else:
                        self.logger.info("Writing file [{}]".format(output_file))
                        CFNYAMLHandler.validate_output_dir(os.path.split(output_file)[0])
                        with open(output_file, 'w') as updated_file:
                            updated_file.writelines(file_data)
                        updated_file.close()
                except UnicodeDecodeError:
                    if self._dry_run:
                        self.logger.info("[WHAT IF DRY RUN]: Ran into a (UnicodeDecodeError) problem trying to read the file [{}]. Skipping but copying.".format(current_file))
                    else:
                        self.logger.warning("Ran into a (UnicodeDecodeError) problem trying to read the file [{}]. Skipping but copying.".format(current_file))
                        self._copy_file(current_file, output_file)
                except TaskCatException:
                    raise
                except Exception as e:
                    raise e

    def rewrite_and_upload(self):
        """
        This function performs both a rewrite and upload of files by calling each respective function consecutively.
        """
        self.rewrite_only()
        self.upload_only()

    def _get_file_list(self, input_path):
        if not self._file_list:
            _file_list = []
            if os.path.isfile(input_path):
                _file_list.append(input_path)
            elif os.path.isdir(input_path):
                for root, dirs, files in os.walk(input_path):
                    for _current_file in files:
                        if not _current_file.endswith(tuple(self._GIT_EXT)):
                            _file_list.append(os.path.join(root, _current_file))
                    for directory in self._EXCLUDED_DIRS:
                        if directory in dirs:
                            dirs.remove(directory)
            else:
                raise TaskCatException("Directory/File is non-existent. Aborting.")
            self._file_list = _file_list
        return self._file_list

    def _string_rewriter(self, current_string):
        if self._prod_bucket_name in current_string:
            # If the path is s3/http/https
            if any(x in current_string for x in ['s3:', 'http:', 'https:']):
                # Make sure that it's part of the target key prefix (that is, part of this repo)
                if self._target_key_prefix in current_string:
                    self.logger.info("Rewriting [{}]".format(current_string.rstrip('\n\r')))
                    return current_string.replace(self._prod_bucket_name, self._target_bucket_name)
                # If it's not then, it's a reference that should not be touched
                else:
                    self.logger.info("NOT rewriting [{}] because it's not part of this repo".format(current_string.rstrip('\n\r')))
                    return current_string
            # Else just replace the bucket name
            else:
                self.logger.info("Rewriting [{}]".format(current_string.rstrip('\n\r')))
                return current_string.replace(self._prod_bucket_name, self._target_bucket_name)
        elif self._prod_key_prefix in current_string:
            self.logger.info("Rewriting [{}]".format(current_string.rstrip('\n\r')))
            return current_string.replace(self._prod_key_prefix, self._target_key_prefix)
        else:
            return current_string

    def _recurse_nodes(self, current_node):
        if type(current_node) in [OrderedDict, dict]:
            for key in current_node.keys():
                self.logger.debug("Key: ")
                self.logger.debug(key)
                self.logger.debug("Type: ")
                self.logger.debug(type(current_node[key]))
                self.logger.debug("Value: ")
                self.logger.debug(current_node[key])
                current_node[key] = self._recurse_nodes(current_node[key])
        elif type(current_node) is list:
            for _index, item in enumerate(current_node):
                self.logger.debug("Type: ")
                self.logger.debug(type(item))
                self.logger.debug("Value: ")
                self.logger.debug(item)
                current_node[_index] = self._recurse_nodes(item)
            return current_node
        elif type(current_node) is str:
            return self._string_rewriter(current_node)
        elif type(current_node) is bool:
            self.logger.debug("Not much we can do with booleans. Skipping.")
        elif type(current_node) in [int, float]:
            self.logger.debug("Not much we can do with numbers. Skipping.")
        elif type(current_node) in [datetime.date, datetime.time, datetime.datetime, datetime.timedelta]:
            self.logger.debug("Not much we can do with datetime. Skipping.")
        elif type(current_node) is None:
            self.logger.debug("Not much we can do with nulls. Skipping.")
        else:
            self.logger.error("Unsupported type.")
            self.logger.error("Failing Type: ")
            self.logger.error(type(current_node))
            self.logger.error("Failing Value: ")
            self.logger.error(current_node)
            raise TaskCatException("Unsupported type.")

        self.logger.debug("PARSED!")

        return current_node

    def _copy_file(self, in_file, out_file):
        CFNYAMLHandler.validate_output_dir(os.path.split(out_file)[0])
        # copy only if it's a new location for the output
        if in_file is not out_file:
            shutil.copyfile(in_file, out_file)

    def aws_api_init(self, aws_profile=None, aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None):
        """
        This function reads the AWS credentials to ensure that the client has right credentials defined to successfully
        authenticate against an AWS account. It could be either profile name, access key and secret key or none.
        :param aws_profile: AWS profile name.
        :param aws_access_key_id: access key ID secret key.
        :param aws_secret_access_key: AWS secret access key.
        """
        if aws_profile is not None:
            if not (aws_secret_access_key is None and aws_access_key_id is None):
                self.logger.error("Cannot use aws_profile with aws_access_key_id or aws_secret_access_key")

        if aws_profile:
            self._auth_mode = 'profile'
            self._aws_profile = aws_profile
        elif aws_access_key_id and aws_secret_access_key:
            self._auth_mode = 'keys'
            self._aws_access_key_id = aws_access_key_id
            self._aws_secret_access_key = aws_secret_access_key
            self._aws_session_token = aws_session_token
        else:
            self._auth_mode = 'environment'
        try:
            sts_client = self._boto_clients.get(
                'sts',
                credential_set='alchemist',
                aws_access_key_id=self._aws_access_key_id,
                aws_secret_access_key=self._aws_secret_access_key,
                aws_session_token=self._aws_session_token,
                profile_name=self._aws_profile,
                region=self.get_default_region()
            )
            account = sts_client.get_caller_identity().get('Account')
        except TaskCatException:
            raise
        except Exception as e:
            try:
                self.logger.warning('Trying GovCloud region.')
                self.set_default_region('us-gov-west-1')
                sts_client = self._boto_clients.get(
                    'sts',
                    credential_set='alchemist',
                    aws_access_key_id=self._aws_access_key_id,
                    aws_secret_access_key=self._aws_secret_access_key,
                    aws_session_token=self._aws_session_token,
                    profile_name=self._aws_profile,
                    region=self.get_default_region()
                )
                account = sts_client.get_caller_identity().get('Account')
            except TaskCatException:
                raise
            except Exception as e:
                self.logger.error("Credential Error - Please check you {}!".format(self._auth_mode))
                self.logger.debug(str(e))
                raise TaskCatException("Credential Error - Please check you {}!".format(self._auth_mode))
        self.logger.info("AWS AccountNumber: \t [%s]" % account)
        self.logger.info("Authenticated via: \t [%s]" % self._auth_mode)

    @staticmethod
    def interface():
        """
        This function creates an argparse parser, parses the arguments, and returns an args object.

        :return: An object from argparse which contains all the args passed in from the command line.
        """
        # Creating Parser
        parser = argparse.ArgumentParser(
            prog="alchemist",
            description="AWS Quick Start rewriter and uploader of assets."
        )
        parser.add_argument(
            "input_path",
            type=str,
            help="the input path of assets to rewrite and/or upload."
        )
        parser.add_argument(
            "-sb",
            "--source-bucket-name",
            type=str,
            help="source S3 bucket name for rewrite."
        )
        parser.add_argument(
            "target_bucket_name",
            type=str,
            help="target S3 bucket name for rewrite and/or upload."
        )
        parser.add_argument(
            "-t",
            "--target-key-prefix",
            type=str,
            help="target S3 key prefix to use. This is required when uploading."
        )
        parser.add_argument(
            "-sp",
            "--source-key-prefix",
            type=str,
            help="source S3 key prefix name for rewrite."
        )
        parser.add_argument(
            "-o",
            "--output-directory",
            type=str,
            help="custom output directory path. If no path is specified, will overwrite current file(s)."
        )
        parser.add_argument(
            "-b",
            "--basic-rewrite",
            action='store_true',
            help="specify to perform a basic rewrite vs. walking the document."
        )
        actions = parser.add_mutually_exclusive_group(required=True)
        actions.add_argument(
            "-u",
            "--upload-only",
            action='store_true',
            help="specify to only upload to S3 (no rewrite)."
        )
        actions.add_argument(
            "-r",
            "--rewrite-only",
            action='store_true',
            help="specify to only rewrite (no upload)."
        )
        actions.add_argument(
            "-ru",
            "--rewrite-and-upload",
            action='store_true',
            help="specify to rewrite and upload to S3."
        )
        parser.add_argument(
            "--convert-key-prefix-to-slashes",
            action='store_true',
            help="specify to convert a quickstart-some-repo/ key prefix to a some/repo/latest/ key prefix."
        )
        parser.add_argument(
            "-p",
            "--aws-profile",
            type=str,
            help="use existing AWS credentials profile."
        )
        parser.add_argument(
            "-a",
            "--aws-access-key-id",
            type=str,
            help="AWS access key ID."
        )
        parser.add_argument(
            "-s",
            "--aws-secret-access-key",
            type=str,
            help="AWS secret access key."
        )
        parser.add_argument(
            "-st",
            "--aws-session-token",
            type=str,
            help="AWS secret access key."
        )
        parser.add_argument(
            "--verbose",
            action='store_true',
            help="specify to enable debug mode logging."
        )
        parser.add_argument(
            "--dry-run",
            action='store_true',
            help="specify to simulate the rewrite and upload actions to learn what would happen."
        )

        args = parser.parse_args()

        if args.aws_profile is not None:
            if not (args.aws_secret_access_key is None and args.aws_access_key_id is None):
                parser.error("Cannot use -p/--aws-profile with -a/--aws-access-key-id or -s/--aws-secret-access-key")

        if args.upload_only and args.output_directory:
            parser.error("Upload only mode does not use an output directory")

        if args.upload_only or args.rewrite_and_upload:
            if args.target_key_prefix is None:
                parser.error("-t/--target-key-prefix must be provided when uploading is specified (-u/--upload-only or -ru/--rewrite-and-upload")

        if args.convert_key_prefix_to_slashes:
            args.target_key_prefix = CFNAlchemist.aws_quickstart_s3_key_prefix_builder(args.target_key_prefix)

        return args

    @staticmethod
    def aws_quickstart_s3_key_prefix_builder(repo_name):
        """
        This converts a quickstart-some-repo/ key prefix string to a some/repo/latest/ key prefix string.

        :return: An object from argparse which contains all the args passed in from the command line.
        """
        # Determine S3 path from a valid git repo name
        # Remove quickstart-, change dashes to slashes, and add /latest
        repo_path = os.path.join(repo_name.replace('quickstart-', '', 1).replace('-', '/'), 'latest/')

        # EXCEPTIONS (that we have to live with for now):
        # enterprise-accelerator
        repo_path = repo_path.replace('enterprise/accelerator', 'enterprise-accelerator', 1)
        # nist-high
        repo_path = repo_path.replace('nist/high', 'nist-high', 1)
        # chef-server
        repo_path = repo_path.replace('chefserver', 'chef-server', 1)
        print("[INFO]: Converted repo name [" + str(repo_name) + "] to S3 path [" + str(repo_path) + "]")
        return repo_path
