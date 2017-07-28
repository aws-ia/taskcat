#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# author: Santiago Cardenas sancard@amazon.com
from __future__ import print_function

import sys
from taskcat import deployer


args = deployer.CFNAlchemist.interface()

cfn_alchemist = deployer.CFNAlchemist()
cfn_alchemist.initialize(args)
cfn_alchemist.aws_api_init(args)

if args.upload_only:
    cfn_alchemist.upload_only()
#elif args.rewrite_only:
#    cfn_alchemist.rewrite_only()
#elif args.rewrite_and_upload:
#    cfn_alchemist.rewrite_and_upload()
else:
    print("[ERROR]: No action specified. Aborting.")
    sys.exit(1)

print("[INFO]: Done.")
