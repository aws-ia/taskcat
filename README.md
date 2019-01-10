# taskcat
[![GitHub release](https://img.shields.io/github/release/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat)

[![taskcat logo](https://raw.githubusercontent.com/aws-quickstart/taskcat/master/assets/docs/images/logo.png)](https://github.com/aws-quickstart/taskcat)
[![GitHub stars](https://img.shields.io/github/stars/aws-quickstart/taskcat.svg?style=social&label=Stars)](https://github.com/aws-quickstart/taskcat)

[![Build Status](https://travis-ci.org/aws-quickstart/taskcat.svg?branch=master)](https://travis-ci.org/aws-quickstart/taskcat)
[![Docker Build Status](https://img.shields.io/docker/build/taskcat/taskcat.svg)](https://hub.docker.com/r/taskcat/taskcat/builds)
[![PyPI version](https://badge.fury.io/py/taskcat.svg)](https://badge.fury.io/py/taskcat)

## What is taskcat?
**taskcat** is a tool that tests AWS CloudFormation templates. It deploys your AWS CloudFormation template in multiple AWS Regions and generates a report with a pass/fail grade for each region. You can specify the regions and number of Availability Zones you want to include in the test, and pass in parameter values from your AWS CloudFormation template. taskcat is implemented as a Python class that you import, instantiate, and run.

TestCat was developed by the AWS QuickStart team to test AWS CloudFormation templates that automatically deploy workloads on AWS. We’re pleased to make the tool available to all developers who want to validate their custom AWS CloudFormation
templates across AWS Regions

### Support
[![Feature Request](https://img.shields.io/badge/Open%20Issues-Feature%20Request-green.svg)](https://github.com/aws-quickstart/taskcat/issues/new/choose)
[![Report Bugs](https://img.shields.io/badge/Open%20Issue-Report%20Bug-red.svg)](https://github.com/aws-quickstart/taskcat/issues/new/choose)
[![Frequently Asked Questions](https://img.shields.io/badge/%20-FAQ-yellowgreen.svg)](FAQ.md)

## Installing taskcat
**taskcat** can be install using `docker` or `pip`

### Installing via docker
![Docker Required](https://img.shields.io/badge/Prerequisites-docker-blue.svg)

```
curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/master/installer/docker-installer.sh | sh
```
Note: (If you do not have root privileges taskcat will install in the current directory)

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

### Running taskcat
Note: If you have AWS credentials sourced (or default boto profile is available)

```
taskcat -c /path/to/your_project/ci/taskcat.yml
```
> If you need to pass ACCESS and SECRET keys
```
taskcat -c /path/to/your_project/ci/taskcat.yml -A YOUR_ACCESS_KEY -S YOUR_SECRET_KEY
```
> If you want to use a different account or profile
```
taskcat -c /path/to/your_project/ci/taskcat.yml -P boto-profile-name
```
### Files you’ll need
* **taskcat.yml** - This file contains the test cases
* **JSON input** - This file contains the inputs that you want to pass to AWS CloudFormation template that is being tested

* Step 1: Building your configuration file
* Step 2: Building your JSON input file.

## Step 1: Creating a taskcat.yml
Open the taskcat.yml file with and editor and update the filenames to match your need.

example here:
[taskcat.yml](https://raw.githubusercontent.com/aws-quickstart/taskcat/master/examples/sample-taskcat-project/ci/taskcat.yml)

#### Example of taskcat.yml
    global:
      owner: owner@company.com
      qsname: sample-cloudformation-project <- Must match the root directory of project (usually the name of git repo)
      #s3bucket: projectx-templates <- (Optional) Only needed if you want to use a specific bucket
      regions:
        - us-east-1
        - us-east-2
        - us-west-1
        - us-west-2
    tests:
      # The following test will test in both us-west-1 and us-east-1 using sample-cloudformation-input.json as inputs
      scenario-1:
        regions:
          - us-west-1
          - us-east-1
        template_file: sample-cloudformation-project-novpc.template
        parameter_input: sample-cloudformation-input-novpc.json
      # The following test will test in both all 4 region defined in the global region section using sample-cloudformation-input.json as inputs
          scenario-all-regions:
        parameter_input: sample-cloudformation-input-withvpc.json
        template_file: sample-cloudformation-project-withvpc.template

#### Example of project directory structure
    sample-cloudformation-project/
    ├── LICENSE.txt
    ├── README.md
    ├── ci
    │   ├── taskcat.yml <- This the config file that will hold all the test definitions
    │   ├──  sample-cloudformation-input-novpc.json <-  This file contain input that will pass in during stack creation [vpc version] (See auto parms for more info)
    │   └──  sample-cloudformation-input-withvpc.json <-  This file contain input that will pass in during stack creation [no-vpc version](See auto parms for more info)
    ├── scripts
    │   └── userdata.sh <- If you have userdata scripts you can load then in the scripts directory
    ├── submodules  <- If you have git submodules you can load them in the submodules directory
    │   └── quickstart-aws-vpc
    │       └── templates
    │           └── aws-vpc.template
    └── templates
        ├── sample-cloudformation-project-novpc.template
        └── sample-cloudformation-project-withvpc.template <- Second version on template that will create a vpc with the workload

## Step 2: Building a json input file 
The example below shows an input file for a stack that requires seven parameters `KeyPairName`,`InstanceType`, `AvailablityZones`, `RandomString`, `RandomNumbers`, `GenerateUUID` and `Password`

Note: you can auto generate values at runtime using **taskcat runtime injection** (see example below).

> The following json will evaluate

#### From:

```
[{
    "ParameterKey": "KeyPairName",
    "ParameterValue": "mykey"
}, {
    "ParameterKey": "InstanceType",
    "ParameterValue": "t2.small"
}, {
    "ParameterKey": "AvailablityZones",
    "ParameterValue": "$[taskcat_genaz_2]"
}, {
    "ParameterKey": "RandomString",
    "ParameterValue": "$[taskcat_random-string]"
}, {
    "ParameterKey": "RandomNumbers",
    "ParameterValue": "$[taskcat_random-numbers]"
}, {
    "ParameterKey": "GenerateUUID",
    "ParameterValue": "$[taskcat_genuuid]"
}, {
    "ParameterKey": "Password",
    "ParameterValue": "$[taskcat_genpass_8A]"
}, {
    "ParameterKey": "PasswordConfirm",
    "ParameterValue": "$[taskcat_getval_Password]"
}]
```

#### To:

```
[{
    "ParameterKey": "KeyPair",
    "ParameterValue": "mykey"
}, {
    "ParameterKey": "InstanceType",
    "ParameterValue": "t2.small"
} {
    "ParameterKey": "AvailablityZones",
    "ParameterValue": "us-east-1a, us-east1b"
}, {
    "ParameterKey": "RandomString",
    "ParameterValue": "yysuawpwubvotiqgwjcu"
}, {
    "ParameterKey": "RandomNumbers",
    "ParameterValue": "56188163597280820763"
}, {
    "ParameterKey": "GenerateUUID",
    "ParameterValue": "1c2e3483-2c99-45bb-801d-8af68a3b907b"
}, {
    "ParameterKey": "Password",
    "ParameterValue": "tI8zN3iX8"
}, {
    "ParameterKey": "PasswordConfirm",
    "ParameterValue": "tI8zN3iX8"
}]
```

#### More information on taskcat runtime injection

### (Passwords)
Value that matches the following pattern will be replaced:
 * All runtime injection parameters must start with `$[`
 * Parameters must end with` ]`

To generate a random 8 character alpha-numeric password for testing use $[taskcat_genpass_8] as the value in the json input file
 * The number (8) in the injection string tells taskcat you want a password that character long.
 * Changing the 8 to 12 would result in a 12 character string

(Optionally - you can specify the type of password by adding A or S)

 * A alpha-numeric passwords
 * S passwords with special characters

> Example: $[taskcat_genpass_8A]

> Generates: tI8zN3iX8

> Example: $[taskcat_genpass_8S]

> Generates: mA5@cB5!

### (Availability Zones)
Value that matches the following pattern will be replaced

* Parameters must start with $[
* Parameters must end with ]
* genaz in invoked when taskcat_genaz_X is found
* A number of AZ's will be selected from the region the stack is attempting to launch

> Example: $[taskcat_genaz_2]

> Generates: us-east-1a, us-east-2b

> (if the region is us-east-1)

### (Auto generated s3 bucket )
> Example: $[taskcat_autobucket]

> Generates: evaluates to auto generated bucket name (taskcat-tag-sample-taskcat-project-5fba6597)

### (Generate UUID String)
> Example: $[taskcat_genuuid]

> Generates: 1c2e3483-2c99-45bb-801d-8af68a3b907b

### (Generate Random Values)
String:

> Example: $[taskcat_random-string]

> Generates: yysuawpwubvotiqgwjcu

Numbers:

> Example: $[taskcat_random-numbers]

> Generates: 56188163597280820763

### (Retrieve previously generated value based on parameter name)
UseCase: Need to confirm a dynamically generated password

`"ParameterKey": "MyAppPassword"`

`"ParameterValue": "$[taskcat_genpass_8A]"`

> Generates: pI8zN4iX8

`"ParameterKey": "ConfirmMyAppPassword"`

`"ParameterValue": "$[taskcat_getval_MyAppPassword]"`

> Generates: pI8zN4iX8

[More info here](https://aws-quickstart.github.io/input-files.html)

### Local Parameter Overrides.
In certain situations it may be desirable to introduce local Parameter Override values. taskcat supports this via two files.

The first is located .aws directory within the home-directory of the running user.

```
~/.aws/taskcat_global_override.json
```

The second applies per-project and is located the 'ci' directory.
```
<project_name>/ci/taskcat_project_override.json
```

Parameters defined in either file will supersede parameters within the normal parameter files. The override includes are read in the following order.
- Home Directory (~/.aws/taskcat_global_override.json)
- Project Directory (ci/taskcat_project_override.json)

Note: Keys defined in the Project override with supersede the same keys defined in the global override.
[More info here](https://aws-quickstart.github.io/input-files.html#parm-override)

### Packaging lambda functions
taskcat can automatically zip lambda function source found in `functions/source/*` folders. folders are zipped up and
placed in `functions/packages/FunctionName/lambda.zip`. To enable this functionality you will need to enable it in your
`taskcat.yaml` file by adding `package-lambda: true` to the `global` section:

```yaml
global:
  package-lambda: true
  ...
```

Additionally, taskcat can be set to package zips and then exit without taking any other actions. This can be done by
setting the `-b` or `--lambda-build-only` flag.

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
