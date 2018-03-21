#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# author: Santiago Cardenas <sancard@amazon.com>
from __future__ import print_function

import sys
from taskcat import deployer

if sys.version_info[0] < 3:
    raise Exception("Please use Python 3")

args = deployer.CFNAlchemist.interface()
cfn_alchemist = deployer.CFNAlchemist(
    input_path=args.input_path,
    target_bucket_name=args.target_bucket_name,
    source_bucket_name=args.source_bucket_name,
    target_key_prefix=args.target_key_prefix,
    output_directory=args.output_directory,
    rewrite_mode=deployer.CFNAlchemist.BASIC_REWRITE_MODE if args.basic_rewrite else deployer.CFNAlchemist.OBJECT_REWRITE_MODE,
    verbose=args.verbose,
    dry_run=args.dry_run
)

cfn_alchemist.aws_api_init(
    aws_profile=args.aws_profile,
    aws_access_key_id=args.aws_access_key_id,
    aws_secret_access_key=args.aws_secret_access_key
)

if args.upload_only:
    cfn_alchemist.upload_only()
elif args.rewrite_only:
    cfn_alchemist.rewrite_only()
elif args.rewrite_and_upload:
    cfn_alchemist.rewrite_and_upload()
else:
    print("[ERROR]: No action specified. Aborting.")
    sys.exit(1)

print("[INFO]: Done.")
