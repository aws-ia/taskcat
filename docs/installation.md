
## Installation

Currently only installation via pip is supported.

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

!!! note
    docker is only required if building lambda functions using a Dockerfile

### Installing via pip3

```python
pip3 install taskcat
```
### Installing via pip3 --user
*will install taskcat into homedir, useful if you get permissions errors with the regular method*

```python
pip3 install taskcat --user
```

???+note
    The user install dir is platform specific

    On Mac:

    - `~/Library/Python/3.x/bin/taskcat`

    On Linux:

    - `~/.local/bin`

!!! warning
    Be sure to add the python bin dir to your **$PATH**

### Windows

Taskcat on Windows is **not supported**.

If you are running Windows 10 we recommend that you install [Windows Subsystem for Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/about) and then install taskcat inside the WSL environment. For details, see [Install and configure TaskCat on Microsoft Windows 10](https://aws.amazon.com/blogs/infrastructure-and-automation/install-and-configure-taskcat-on-microsoft-windows-10/).
