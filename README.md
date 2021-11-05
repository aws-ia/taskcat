[![logo](https://raw.githubusercontent.com/aws-ia/taskcat/main/assets/docs/images/tcat.png)](https://taskcat.io/)
[![Build Status](https://travis-ci.com/aws-ia/taskcat.svg?branch=main)](https://travis-ci.com/aws-ia/taskcat) [![PyPI version](https://badge.fury.io/py/taskcat.svg)](https://badge.fury.io/py/taskcat) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)



## What is TaskCat?
**TaskCat** is a tool that tests AWS CloudFormation templates. It deploys your AWS
CloudFormation template in multiple AWS Regions and generates a report with a pass/fail
grade for each region. You can specify the regions and number of Availability Zones you
want to include in the test, and pass in parameter values from your AWS CloudFormation
template. TaskCat is implemented as a Python class that you import, instantiate, and run.

TaskCat was developed by the aws-ia team to test AWS CloudFormation templates
that automatically deploy workloads on AWS. We’re pleased to make the tool available to
all developers who want to validate their custom AWS CloudFormation templates across
AWS Regions

__See [TaskCat documentation](https://aws-ia.github.io/taskcat/).__

## Support
[![Feature Request](https://img.shields.io/badge/Open%20Issues-Feature%20Request-green.svg)](https://github.com/aws-ia/taskcat/issues/new/choose)
[![Report Bugs](https://img.shields.io/badge/Open%20Issue-Report%20Bug-red.svg)](https://github.com/aws-ia/taskcat/issues/new/choose)

## GitHub

[![GitHub stars](https://img.shields.io/github/stars/aws-ia/taskcat.svg?style=social&label=Stars)](https://github.com/aws-ia/taskcat)
[![GitHub issues](https://img.shields.io/github/issues/aws-ia/taskcat.svg)](https://github.com/aws-ia/taskcat/issues)
[![GitHub closed issues](https://img.shields.io/github/issues-closed-raw/aws-ia/taskcat.svg)](https://github.com/aws-ia/taskcat/issues?q=is%3Aissue+is%3Aclosed)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/aws-ia/taskcat.svg)](https://github.com/aws-ia/taskcat/pulls)
[![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/aws-ia/taskcat.svg)](https://github.com/aws-ia/taskcat/pulls?q=is%3Apr+is%3Aclosed)

## PyPi

[![PyPI - Downloads](https://img.shields.io/pypi/dw/taskcat.svg)](https://pypi.org/project/taskcat/#history)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/taskcat.svg)](https://pypi.org/project/taskcat/#history)
