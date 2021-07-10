![logo](https://aws-ia.github.io/assets/img/taskcat-bg.png)

# taskcat
[![Build Status](https://travis-ci.com/aws-quickstart/taskcat.svg?branch=main)](https://travis-ci.com/aws-quickstart/taskcat)
[![PyPI version](https://badge.fury.io/py/taskcat.svg)](https://badge.fury.io/py/taskcat)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**[Installation](#Installation)**

**[Usage](#Usage)**

## What is taskcat?
**taskcat** is a tool that tests AWS CloudFormation templates. It deploys your AWS
CloudFormation template in multiple AWS Regions and generates a report with a pass/fail
grade for each region. You can specify the regions and number of Availability Zones you
want to include in the test, and pass in parameter values from your AWS CloudFormation
template. taskcat is implemented as a Python class that you import, instantiate, and run.

taskcat was developed by the aws-ia team to test AWS CloudFormation templates
that automatically deploy workloads on AWS. We’re pleased to make the tool available to
all developers who want to validate their custom AWS CloudFormation templates across
AWS Regions


## Support
[![Feature Request](https://img.shields.io/badge/Open%20Issues-Feature%20Request-green.svg)](https://github.com/aws-quickstart/taskcat/issues/new/choose)
[![Report Bugs](https://img.shields.io/badge/Open%20Issue-Report%20Bug-red.svg)](https://github.com/aws-quickstart/taskcat/issues/new/choose)

## Installation

Currently only installation via pip is supported. Installation via docker coming soon.

### Requirements
![Python pip](https://img.shields.io/badge/Prerequisites-pip-blue.svg)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/taskcat.svg)](https://pypi.org/project/taskcat/#history)
![Python pip](https://img.shields.io/badge/Prerequisites-docker-yellow.svg)

The host taskcat is run on requires access to an AWS account, this can be done by any
of the following mechanisms:

1. Environment variables
2. Shared credential file (~/.aws/credentials)
3. AWS config file (~/.aws/config)
4. Assume Role provider
5. Boto2 config file (/etc/boto.cfg and ~/.boto)
6. Instance metadata service on an Amazon EC2 instance that has an IAM role configured.

for more info see the [boto3 credential configuration documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html).

> Note: docker is only required if building lambda functions using a Dockerfile

### Installing via pip3

```
pip3 install taskcat
```
### Installing via pip3 --user
*will install taskcat into homedir, useful if you get permissions errors with the regular method*

```
pip3 install taskcat --user
```

> Note: the user install dir is platform specific

*For Example:* (On Mac: ~/Library/Python/3.x/bin/taskcat)

*For Example:* (On Linux: ~/.local/bin)

> **Warning:** Be sure to add the python bin dir to your **$PATH**

### Windows
taskcat on Windows is **not supported**.

If you are running Windows 10 we recommend that you install [Windows Subsystem for Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/about) and then install taskcat inside the WSL environment using the steps above.

## Usage

### CLI
The cli is self documenting by using `--help`. The most common use of taskcat is for
executing function tests of CloudFormation templates. The command for this is:

```bash
taskcat test run
```

add `--help to see the supported flags and arguments`

### Python
Taskcat can be imported into Python and used in the testing framework of your choice.
```python
from taskcat.testing import CFNTest

test = CFNTest.from_file(project_root='./template_dir')

with test as stacks:
    # Calling 'with' or 'test.run()' will deploy the stacks.
    for stack in stacks:
        print(f"Testing {stack.name}")

        bucket_name = ""

        for output in stack.outputs:

            if output.key == "LogsBucketName":
                bucket_name = output.value
                break

        assert "logs" in bucket_name

        assert stack.region.name in bucket_name

        print(f"Created bucket: {bucket_name}")
```

The example used here is very simple, you would most likely leverage other python modules like boto3 to do more advanced testing. The `CFNTest` object can be passed the same arguments as `taskcat test run`. See the [docs](https://aws-quickstart.github.io/taskcat/apidocs/taskcat/testing/index.html) for more details.

### Config files
taskcat has several configuration files which can be used to set behaviors in a flexible way.

#### Global config
`~/.taskcat.yml` provides global settings that become defaults for all projects.

```
 # General configuration settings
 general                 
   auth # AWS authentication section
      <AUTH_NAME>
   parameters: # Parameter key-values to pass to cfn  (global parameters take precedence) 
      <PARAMETER_NAME>    

   s3_bucket: # Name of S3 bucket to upload project to (if left out a bucket will be auto-generated)
   s3_regional_buckets: # Boolean flag to upload the project to a bucket (generated in each region specified)
   tags: # Tags to apply to CloudFormation template
      TAG_NAME
```
#### Project config

> File location: <PROJECT_ROOT>/.taskcat.yml` provides project specific configuration.

```
project         # Project specific configuration section
  auth          # AWS authentication section
    <AUTH_NAME>
  az_blacklist  # List of Availability Zones ID's to exclude when generating availability zones
  build_submodules # Build Lambda zips recursively for submodules, set to false to disable
  lambda_source_path # Path relative to the project root containing Lambda zip files, default is 'lambda_functions/source'
  lambda_zip_path    # Path relative to the project root to place Lambda zip files, default is 'lambda_functions/zips'
  name               # Project name, used as s3 key prefix when uploading objects
  owner              # Email address for project owner (not used at present)
  package_lambda     # Package Lambda functions into zips before uploading to s3, set to false to disable
  parameters         # Parameter key-values to pass to CloudFormation, parameters provided in global config take precedence
    <PARAMETER_NAME>
  regions            # List of AWS regions
  s3_bucket          # Name of S3 bucket to upload project to, if left out a bucket will be auto-generated
  s3_enable_sig_v2   # Enable (deprecated) sigv2 access to auto-generated buckets
  s3_object_acl      # ACL for uploaded s3 objects, defaults to 'private'
  tags               # Tags to apply to CloudFormation template
    <TAG_NAME>
  template           # path to template file relative to the project config file path

tests:
    auth            # AWS authentication section
      <AUTH_NAME>
    az_blacklist    # List of Availability Zones ID's to exclude when generating availability zones
    parameters      # Parameter key-values to pass to CloudFormation, parameters provided in global config take precedence
      <PARAMETER_NAME>
    regions         # List of AWS regions
    s3_bucket       # Name of S3 bucket to upload project to, if left out a bucket will be auto-generated
    tags            # Tags to apply to CloudFormation template
      <TAG_NAME>
    template        # Path to template file relative to the project config file path

> At minimum it must provide a project name, list of regions, template name and one test.

Minimal example:

```yaml
project:
  name: my-cfn-project
  regions:
  - us-west-2
  - eu-north-1
tests:
  default:
    template: ./templates/my-template.yaml
```

> Complete example with comments: [tests/data/config_full_example/.taskcat.yml](https://raw.githubusercontent.com/taskcat/taskcat/master/tests/data/config_full_example/.taskcat.yml)

### Parameter overrides
a parameter override file can be created in `<PROJECT_ROOT>/.taskcat_overrides.yml`.
Parameter Keys/Values specified in this file take precedence over values defined in all
other configuration files. For example:

```yaml
KeyPair: my-overriden-keypair
VpcId: vpc-1234abcd
```

> Warning: it is recommended to add `.taskcat_overrides.yml` to `.gitignore` to ensure
>it is not accidentally checked into source control

#### Precedence
With the exception of the `parameters` section, more specific config with the same key
takes precedence.

> The rationale behind having parameters function this way is so that values can be
overridden at a system level outside of a project, that is likely committed to source
control. parameters that define account specific things like VPC details, Key Pairs, or
secrets like API keys can be defined per host outside of source control.

For example, consider this global config:

`~/.taskcat.yml`
```yaml
general:
  s3_bucket: my-globally-defined-bucket
  parameters:
    KeyPair: my-global-ec2-keypair
```

Given a simple project config:

```yaml
project:
  name: my-project
  regions:
  - us-east-2
tests:
  default:
    template: ./template.yaml
```

The effective test configuration would become:

```yaml
tests:
  default:
    template: ./template.yaml
    s3_bucket: my-globally-defined-bucket
    parameters:
      KeyPair: my-global-ec2-keypair
```

If any item is re-defined in a project it takes precedence over the global value.
Anything defined in a test takes precedence over what is defined in the project or
global configuration. with the **exception** of the `parameters` section which works in
reverse. For example, using the same global config as above, given this project config:

```yaml
project:
  name: my-project
  regions:
  - us-east-2
  s3_bucket: my-project-s3-bucket
tests:
  default:
    template: ./template.yaml
    parameters:
      KeyPair: my-test-ec2-keypair
```

Would result in this effective test configuration:

```yaml
tests:
  default:
    template: ./template.yaml
    s3_bucket: my-project-s3-bucket
    parameters:
      KeyPair: my-global-ec2-keypair
```

Notice that `s3_bucket` took the most specific value and `KeyPair` the most general.

### CLI interface

taskcat adopts a similar cli command structure to `git` with a
`taskcat command subcommand --flag` style. The cli is also designed to be simplest if
run from the root of a project. Let's have a look at equivalent command to run a test:


cd into the project root and type __test__ __run__:

```bash
cd ./quickstart-aws-vpc
taskcat test run
```

or run it from anywhere by providing the path to the project root
```bash
taskcat test run -p ./quickstart-aws-vpc
```

### Non-standard credentials

taskcat leverages the credential mechanisms of the AWS CLI, with the exception of environment variables. To integrate advanced credential handling (such as AWS SSO), [please see issue #596 for an example]( https://github.com/aws-quickstart/taskcat/issues/596)

### Configuration files
The configuration files required for taskcat have changed, to ease migration, if taskcat
is run and legacy config files are found, they are converted and written to new file
locations. For more information on the new format, see the [config file docs](#config-files).

----
**GitHub:**

[![GitHub stars](https://img.shields.io/github/stars/aws-quickstart/taskcat.svg?style=social&label=Stars)](https://github.com/aws-quickstart/taskcat)
[![GitHub issues](https://img.shields.io/github/issues/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/issues)
[![GitHub closed issues](https://img.shields.io/github/issues-closed-raw/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/issues?q=is%3Aissue+is%3Aclosed)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/pulls)
[![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/aws-quickstart/taskcat.svg)](https://github.com/aws-quickstart/taskcat/pulls?q=is%3Apr+is%3Aclosed)

**PyPi:**

[![PyPI - Downloads](https://img.shields.io/pypi/dw/taskcat.svg)](https://pypi.org/project/taskcat/#history)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/taskcat.svg)](https://pypi.org/project/taskcat/#history)
