#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# author: Santiago Cardenas <sancard@amazon.com>

import os
import sys
import argparse
import json
import logging
from collections import OrderedDict
from taskcat import utils

if sys.version_info[0] < 3:
    raise Exception("Please use Python 3")

# create logger
logger = logging.getLogger('beautycorn')
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

parser = argparse.ArgumentParser(description='AWS Quick Start JSON/YAML beautifier')
parser.add_argument("path", type=str, help='specify the path of template file(s)')
args = parser.parse_args()

TEMPLATE_EXT = ['.template', '.json', '.yaml', '.yml']

files = []
# Checks if path is directory. If so, updates all .template files
if os.path.isdir(args.path):
    for dir_path, dir_name, file_names in os.walk(args.path):
        for file_name in file_names:
            if file_name.endswith(tuple(TEMPLATE_EXT)):
                files.append(os.path.join(dir_path, file_name))
elif os.path.isfile(args.path):
    files.append(args.path)
else:
    logger.error("Directory/File is non-existent. Aborting.")
    sys.exit(1)

# TODO: Enforce sections in specific order. Ordering tbd..
for current_file in files:
    if current_file.endswith(tuple(TEMPLATE_EXT)):
        logger.info("Opening file [{}]".format(current_file))

        with open(current_file, 'r', newline=None) as template:
            template_raw_data = template.read()
            template.close()

        template_raw_data = template_raw_data.strip()

        if template_raw_data[0] in ['{', '['] and template_raw_data[-1] in ['}', ']']:
            logger.info('Detected JSON. Loading file.')
            FILE_FORMAT = 'JSON'
            template_data = json.load(open(current_file, 'r', newline=None), object_pairs_hook=OrderedDict)
        else:
            logger.info('Detected YAML. Loading file.')
            FILE_FORMAT = 'YAML'
            template_data = utils.CFNYAMLHandler.ordered_safe_load(open(current_file, 'r', newline=None), object_pairs_hook=OrderedDict)

        with open(current_file, 'w') as updated_template:
            logger.info("Writing file [{}]".format(current_file))
            if FILE_FORMAT == 'JSON':
                updated_template.write(json.dumps(template_data, indent=4, separators=(',', ': ')))
            elif FILE_FORMAT == 'YAML':
                updated_template.write(utils.CFNYAMLHandler.ordered_safe_dump(template_data, indent=2, allow_unicode=True, default_flow_style=False, explicit_start=True, explicit_end=True))
        updated_template.close()
    else:
        logger.warning("File type not supported. Please use .template file.")
        continue
