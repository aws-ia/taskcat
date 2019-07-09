#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function

import logging
import os
from multiprocessing import Pool
from shutil import make_archive

from taskcat._common_utils import make_dir

LOG = logging.getLogger(__name__)


class LambdaBuild:
    """Zips contents of lambda source files.

    """

    zip_file_name = "lambda"

    def __init__(self, source_path, output_path="../packages", threads=4):

        cur_dir = os.path.abspath(os.curdir)
        try:
            self.source_path = os.path.abspath(source_path)
            os.chdir(self.source_path)
            self.output_path = os.path.abspath(output_path)

            dirs = [i for i in os.listdir("./") if os.path.isdir(i)]
            pool = Pool(threads)
            pool.map(self._make_zip, dirs)
            pool.close()
            pool.join()
        finally:
            os.chdir(cur_dir)

    def _make_zip(self, name):
        try:
            LOG.info("Zipping lambda function %s" % name)
            output_path = "%s/%s" % (self.output_path, name)
            make_dir(output_path)
            os.chdir(name)
            make_archive(output_path + "/" + self.zip_file_name, "zip", "./")
        finally:
            os.chdir(self.source_path)
