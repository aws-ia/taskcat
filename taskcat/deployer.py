#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# author: sancard@amazon.com
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
from .utils import ClientFactory
from .utils import CFNYAMLHandler


class CFNAlchemist(object):
    OBJECT_REWRITE_MODE = 10
    BASIC_REWRITE_MODE = 20

    def __init__(
        self,
        input_path,
        target_bucket_name,
        target_key_prefix=None,
        output_directory=None,
        rewrite_mode=OBJECT_REWRITE_MODE,
        debug=False,
        dry_run=False
    ):
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
        self._UNSUPPORTED_EXT = ['.bz2', '.gz', '.tar', '.zip', '.rar', '.md', '.txt', '.gif', '.jpg', '.png', '.svg', 'jq']
        self._TEMPLATE_EXT = ['.template', '.json']
        self._GIT_EXT = ['.git', '.gitmodules', '.gitignore', '.gitattributes']
        self._EXCLUDED_DIRS = ['.git', 'ci', '.idea', '.vs']
        self._prod_bucket_name = 'quickstart-reference'

        # properties
        self._boto_clients = ClientFactory(logger=self.logger)
        self._auth_mode = None
        self._aws_profile = None
        self._aws_access_key_id = None
        self._aws_secret_access_key = None

        # properties with setters/getters
        self._input_path = None
        self._target_bucket_name = None
        self._target_key_prefix = None
        self._output_directory = None
        self._rewrite_mode = self.OBJECT_REWRITE_MODE
        self._default_region = 'us-east-1'
        self._excluded_prefixes = None
        self._debug = False
        self._dry_run = False

        # initialize
        self.set_input_path(input_path)
        self.set_target_bucket_name(target_bucket_name)
        self.set_target_key_prefix(target_key_prefix)
        self.set_output_directory(output_directory)
        if rewrite_mode not in [self.OBJECT_REWRITE_MODE, self.BASIC_REWRITE_MODE]:
            self.logger.error("Invalid rewrite_mode.")
        else:
            self.set_rewrite_mode(rewrite_mode)
        self.set_debug(debug)
        self.set_dry_run(dry_run)

        return

    def set_debug(self, debug):
        self._debug = debug
        if self._debug:
            self.logger.setLevel(logging.DEBUG)
            self.ch.setLevel(logging.DEBUG)

    def get_debug(self):
        return self._debug

    def set_dry_run(self, dry_run):
        self._dry_run = dry_run

    def get_dry_run(self):
        return self._dry_run

    def set_input_path(self, input_path):
        self._input_path = input_path

    def get_input_path(self):
        return self._input_path

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
        if self._target_key_prefix is None:
            self.logger.error('target_key_prefix cannot be None')
            sys.exit(1)
        # TODO: FIGURE OUT BOTO SESSION HANDLING DETAILS
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
        file_list = self._get_file_list(self._output_directory if self._output_directory else self._input_path)

        local_key_dict = {}
        for current_file in file_list:
            local_key_dict[unicode(os.path.join(self._target_key_prefix, current_file.replace(self._output_directory if self._output_directory else self._input_path, '', 1).lstrip('\/')).replace('\\', '/'))] = current_file
        self.logger.debug(local_key_dict.keys())

        remote_to_local_diff = list(set(remote_key_dict.keys()) - set(local_key_dict.keys()))
        self.logger.info("Keys in remote S3 bucket but not in local".format(self._target_key_prefix))
        self.logger.info(remote_to_local_diff)

        local_to_remote_diff = list(set(local_key_dict.keys()) - set(remote_key_dict.keys()))
        self.logger.info("Keys in local but not in remote S3 bucket".format(self._target_key_prefix))
        self.logger.info(local_to_remote_diff)

        self.logger.info("Syncing objects to S3 bucket [{}]".format(self._target_bucket_name))
        for _key in local_key_dict.keys():
            if _key in remote_key_dict:
                self.logger.debug("File [{0}] exists in S3 bucket [{1}]. Verifying MD5 checksum for difference.".format(_key, self._target_bucket_name))
                s3_hash = remote_key_dict[_key].e_tag.strip('"')
                local_hash = hashlib.md5(open(local_key_dict[_key], 'rb').read()).hexdigest()
                self.logger.debug("S3 MD5 checksum (etag) [{}]".format(s3_hash))
                self.logger.debug("Local MD5 checksum     [{}]".format(local_hash))
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
        # Create file list and recurse if args._input_path is directory
        file_list = self._get_file_list(self._input_path)
        self.logger.info("Files to be worked on:")
        self.logger.info(file_list)

        # Validate output
        if self._output_directory is not None:
            if os.path.isdir(self._output_directory):
                # We come here if the file is a directory or does not exist
                CFNYAMLHandler.validate_output_dir(self._output_directory)
            else:
                self.logger.error("The location provided [{}] is not a directory.".format(self._output_directory))
                sys.exit(1)

        self.logger.info("Production S3 bucket name that we are looking for [{}]".format(self._prod_bucket_name))
        self.logger.info("Replacement S3 bucket name that we are rewriting with [{}]".format(self._target_bucket_name))

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
            if current_file.endswith(tuple(self._UNSUPPORTED_EXT)):
                self.logger.warning("[{}] File type not supported. Skipping but copying.".format(current_file))
                CFNYAMLHandler.validate_output_dir(os.path.split(output_file)[0])
                # copy only if it's a new location for the output
                if current_file is not output_file:
                    shutil.copyfile(current_file, output_file)
            elif self._rewrite_mode != self.BASIC_REWRITE_MODE \
                    and current_file.endswith(tuple(self._TEMPLATE_EXT)) \
                    and os.path.dirname(current_file).endswith('/templates'):
                self.logger.info("Opening file [{}]".format(current_file))
                with open(current_file, 'rU') as template:
                    template_raw_data = template.read()
                    template.close()
                template_raw_data = template_raw_data.strip()

                if template_raw_data[0] in ['{', '['] and template_raw_data[-1] in ['}', ']']:
                    self.logger.info('Detected JSON. Loading file.')
                    FILE_FORMAT = 'JSON'
                    template_data = json.load(open(current_file, 'rU'), object_pairs_hook=OrderedDict)
                else:
                    self.logger.info('Detected YAML. Loading file.')
                    FILE_FORMAT = 'YAML'
                    template_data = CFNYAMLHandler.ordered_safe_load(open(current_file, 'rU'), object_pairs_hook=OrderedDict)

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
                        self.logger.warning("[{0}] Unsupported {1} structure. Skipping.".format(current_file, FILE_FORMAT))
                        continue

                    # Write modified template
                    self.logger.info("Writing file [{}]".format(output_file))
                    CFNYAMLHandler.validate_output_dir(os.path.split(output_file)[0])
                    with open(output_file, 'wb') as updated_template:
                        if FILE_FORMAT == 'JSON':
                            updated_template.write(json.dumps(template_data, indent=4, separators=(',', ': ')))
                        elif FILE_FORMAT == 'YAML':
                            updated_template.write(
                                CFNYAMLHandler.ordered_safe_dump(template_data, indent=2, allow_unicode=True, default_flow_style=False, explicit_start=True, explicit_end=True))
                    updated_template.close()
                else:
                    self.logger.warning("[{}] Unsupported file format. Skipping.".format(current_file))
                    continue
            else:
                self.logger.info("Opening file [{}]".format(current_file))
                with open(current_file, 'rU') as f:
                    file_data = f.readlines()

                for index, line in enumerate(file_data):
                    file_data[index] = self._string_rewriter(line, self._target_bucket_name)

                # Write modified file
                self.logger.info("Writing file [{}]".format(output_file))
                CFNYAMLHandler.validate_output_dir(os.path.split(output_file)[0])
                with open(output_file, 'wb') as updated_file:
                    updated_file.writelines(file_data)
                updated_file.close()

    def rewrite_and_upload(self):
        self.rewrite_only()
        self.upload_only()

    def _get_file_list(self, input_path):
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
            self.logger.error("Directory/File is non-existent. Aborting.")
            sys.exit(1)
        return _file_list

    def _string_rewriter(self, current_string, replacement_bucket_name):
        if self._prod_bucket_name in current_string:
            # If the path is s3/http/https
            if any(x in current_string for x in ['s3:', 'http:', 'https:']):
                # Make sure that it's part of the target key prefix (that is, part of this repo)
                if self._target_key_prefix in current_string:
                    self.logger.info("Rewriting [{}]".format(current_string.rstrip('\n\r')))
                    return current_string.replace(self._prod_bucket_name, replacement_bucket_name)
                # If it's not then, it's a reference that should not be touched
                else:
                    self.logger.info("NOT rewriting [{}] because it's not part of this repo".format(current_string.rstrip('\n\r')))
                    return current_string
            # Else just replace the bucket name
            else:
                self.logger.info("Rewriting [{}]".format(current_string.rstrip('\n\r')))
                return current_string.replace(self._prod_bucket_name, replacement_bucket_name)
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
        elif type(current_node) in [unicode, str]:
            return self._string_rewriter(current_node, self._target_bucket_name)
        elif type(current_node) is bool:
            self.logger.debug("Not much we can do with booleans. Skipping.")
        elif type(current_node) in [int, long, float]:
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
            sys.exit(1)

        self.logger.debug("PARSED!")

        return current_node

    def aws_api_init(self, aws_profile=None, aws_access_key_id=None, aws_secret_access_key=None):
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
        else:
            self._auth_mode = 'environment'
        try:
            sts_client = self._boto_clients.get(
                'sts',
                credential_set='alchemist',
                aws_access_key_id=self._aws_access_key_id,
                aws_secret_access_key=self._aws_secret_access_key,
                profile_name=self._aws_profile,
                region=self.get_default_region()
            )
            account = sts_client.get_caller_identity().get('Account')
        except Exception as e:
            self.logger.error("Credential Error - Please check you {}!".format(self._auth_mode))
            self.logger.debug(str(e))
            sys.exit(1)
        self.logger.info("AWS AccountNumber: \t [%s]" % account)
        self.logger.info("Authenticated via: \t [%s]" % self._auth_mode)

    @staticmethod
    def interface():
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
            "--debug",
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
        # Determine S3 path from a valid git repo name
        if repo_name.startswith('quickstart-'):
            # Remove quickstart-, change dashes to slashes, and add /latest
            repo_path = os.path.join(repo_name.replace('quickstart-', '', 1).replace('-', '/'), 'latest/')

            # EXCEPTIONS (that we have to live with for now):
            # enterprise-accelerator
            repo_path = repo_path.replace('enterprise/accelerator', 'enterprise-accelerator', 1)
            # nist-high
            repo_path = repo_path.replace('nist/high', 'nist-high', 1)
            # chef-server
            repo_path = repo_path.replace('chefserver', 'chef-server', 1)
            print("[INFO]: Converted repo name [" + str(args.repo_name) + "] to S3 path [" + str(repo_path) + "]")
            return repo_path
        else:
            print("[ERROR]: Repo name must start with 'quickstart-'. Aborting.")
            sys.exit(1)
