> Please note taskcat is in *pre-release* and will get frequent updates/bugfixes while in inital development

> Current beta release date is: March,20,2017 

# taskcat
> version = '0.1.31'
> This program requires python2 
 
### What is taskcat? 
TaskCat is a python Class that helps deploy your cloudformation templates in multiple regions. You can use TaskCat by importing the module and creating a TaskCat object. 

> This repo example code to help you get started.

### Installing taskcat module via pip
```
pip install taskcat --user
```
## taskcat documentation
### Setting up Test Cases 
To setup taskcat test tests is a two step process:
* Step 1 Define your test in the config.ymal
* Step 2 Build a json input file for your cloudformation template.

#### Step 1 Creating a config.ymal
You can generate a sample config.ymal by running `./tcat.py -ey`
The followung command will create a sample config.ymal
```
./tcat.py -ey | egrep -v '#|^$'  >config.ymal
```
Open the file with and editor and update the filenames to match your need. (See section on working with the ymal file)

#### Step 2 Building a json input file
The example below shows an input file for a stack that requires two parms `KeyPair` and `InstanceType`
```json

    [{
    	"ParameterKey": "KeyPair",
    	"ParameterValue": "mykey"
    }, {
    	"ParameterKey": "InstanceType",
    	"ParameterValue": "t2.small"
    }]
```

#### Example code to instantiate TaskCat
> In the repo you will find tcat.py (This file contain a example of how to create a taskcat object)
> You can either download from the repo or copy and paste the following code to a file called `tcat.py`

```
#!/usr/bin/env python
"""
 authors: tonynv@amazon.com,sancard@amazon.com,sshvans@amazon.com
 Program License: Amazon License
 Python Class License: Apache 2.0
"""

from taskcat import TaskCat
import yaml


def main():
    tcat_instance = TaskCat()
    tcat_instance.welcome('taskcat')
    # Initalize cli interface
    # @TODO Add RestFull Interface
    args = tcat_instance.interface

    # Get configuration from command line arg (-c)
    tcat_instance.set_config(args.config_yml)
    # tcat_instance.set_config('ci/config.yml')
    # Get API Handle - Try all know auth
    tcat_instance.aws_api_init(args)
    # Enable verbose output by default (DEBUG ON)
    tcat_instance.verbose = True
# --Begin
# Check for valid ymal and required keys in config
    if args.config_yml is not None:
        print "[TASKCAT ] :Reading Config form: {0}".format(args.config_yml)

        test_list = tcat_instance.validate_yaml(args.config_yml)

# Load ymal into local taskcat config
        with open(tcat_instance.get_config(), 'r') as cfg:
            taskcat_cfg = yaml.safe_load(cfg.read())
        cfg.close()

        tcat_instance.stage_in_s3(taskcat_cfg)
        tcat_instance.validate_template(taskcat_cfg, test_list)
        tcat_instance.validate_parameters(taskcat_cfg, test_list)
        stackinfo = tcat_instance.stackcreate(taskcat_cfg, test_list, 'tonyv')
        tcat_instance.get_stackstatus(stackinfo, 5)
        tcat_instance.cleanup(stackinfo, 5)

# --End

main()
```

#### To run taskcat
```
python tcat.py 
```
> See below for available flags (you need to pass as input -c at minimum)

### TaskCat CLI Flags
```
  -h, --help   show this help message and exit
  -c CONFIG_YML, --config_yml CONFIG_YML [Configuration yaml] Read configuration from config.yml
  -P BOTO_PROFILE, --boto-profile BOTO_PROFILE Authenticate using boto profile
  -A AWS_ACCESS_KEY, --aws_access_key AWS_ACCESS_KEY AWS Access Key
  -S AWS_SECRET_KEY, --aws_secret_key AWS_SECRET_KEY AWS Secret Key
  -ey, --example_yaml  Prints out example yaml
  -v, --verbose  Enables verbosity
```

### Help
	If you need help or have suggestions you can reach out to via tonynv@amazon.com

*Enjoy!* 
