# taskcat
[![GitHub release](https://img.shields.io/github/release/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat)

[![taskcat logo](https://raw.githubusercontent.com/aws-quickstart/taskcat/master/assets/docs/images/logo.png)](https://github.com/aws-quickstart/taskcat)
[![GitHub stars](https://img.shields.io/github/stars/aws-quickstart/taskcat.svg?style=social&label=Stars)](https://github.com/aws-quickstart/taskcat)

[![Build Status](https://travis-ci.org/aws-quickstart/taskcat.svg?branch=master)](https://travis-ci.org/aws-quickstart/taskcat)

[![PyPI version](https://badge.fury.io/py/taskcat.svg)](https://badge.fury.io/py/taskcat)

## What is taskcat?
**taskcat** is a tool that tests AWS CloudFormation templates. It deploys your AWS CloudFormation template in multiple AWS Regions and generates a report with a pass/fail grade for each region. You can specify the regions and number of Availability Zones you want to include in the test, and pass in parameter values from your AWS CloudFormation template. taskcat is implemented as a Python class that you import, instantiate, and run.

taskcat was developed by the AWS QuickStart team to test AWS CloudFormation templates that automatically deploy workloads on AWS. We’re pleased to make the tool available to all developers who want to validate their custom AWS CloudFormation
templates across AWS Regions

### Support
[![Feature Request](https://img.shields.io/badge/Open%20Issues-Feature%20Request-green.svg)](https://github.com/aws-quickstart/taskcat/issues/new/choose)
[![Report Bugs](https://img.shields.io/badge/Open%20Issue-Report%20Bug-red.svg)](https://github.com/aws-quickstart/taskcat/issues/new/choose)

## Installing taskcat
**taskcat** install via `pip`

### Python Requirements:
![Python pip](https://img.shields.io/badge/Prerequisites-pip-blue.svg)[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/taskcat.svg)](https://pypi.org/project/taskcat/#history)

### Installing via pip3

```
pip3 install taskcat
```
### Installing via pip3 --user
__(for those who want to install taskcat into their homedir)__

```
pip3 install taskcat --user
```

Note: (the user install dir is platform specific)

*For Example:* (On Mac: ~/Library/Python/3.x/bin/taskcat)

*For Example:* (On Linux: ~/.local/bin)

> **Warning:** Be sure to add the python bin dir to your **$PATH**

### Windows
Taskcat on Windows is **not supported**.

If you are running Windows 10 we recommend that you install [Windows Subsystem for Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/about) and then install taskcat inside the WSL environment using the steps above.

### Files you’ll need to use taskcat

* Step 1: You will need to configure your boto profiles (taskcat will use you default profile if none is explictily provided)
* Step 2: Create a taskcat test configurations

example here:
[taskcat.yml](https://raw.githubusercontent.com/taskcat/taskcat/master/tests/data/config_full_example/.taskcat.yml)

----
**GitHub:**

[![GitHub issues](https://img.shields.io/github/issues/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/issues)
[![GitHub closed issues](https://img.shields.io/github/issues-closed-raw/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/issues?q=is%3Aissue+is%3Aclosed)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/pulls)
[![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/pulls?q=is%3Apr+is%3Aclosed)

**PyPi:**

[![PyPI - Downloads](https://img.shields.io/pypi/dw/taskcat.svg)](https://pypi.org/project/taskcat/#history)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/taskcat.svg)](https://pypi.org/project/taskcat/#history)

**Status**

[![Libraries.io for GitHub](https://img.shields.io/librariesio/github/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/network/dependencies)

**License:**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
