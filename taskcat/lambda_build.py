#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function


import os
from shutil import make_archive
from taskcat.colored_console import PrintMsg
from taskcat.common_utils import make_dir

class LambdaBuild(object):
    """Zips contents of lambda source files.

    """

    zip_file_name = "lambda"

    def __init__(self, source_path, output_path="../packages"):

        cur_dir = os.path.abspath(os.curdir)
        try:
            self.source_path = os.path.abspath(source_path)
            os.chdir(self.source_path)
            self.output_path = os.path.abspath(output_path)

            dirs = [ i for i in os.listdir("./") if os.path.isdir(i) ]
            for dir in dirs:
                self._make_zip(dir)
        finally:
            os.chdir(cur_dir)
        return

    def _make_zip(self, name):
        try:
            print(PrintMsg.INFO + "Zipping lambda function %s" % name)
            output_path = "%s/%s" % (self.output_path, name)
            make_dir(output_path)
            os.chdir(name)
            make_archive(output_path + "/" + self.zip_file_name, "zip", "./")
        finally:
            os.chdir(self.source_path)
