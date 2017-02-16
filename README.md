# taskcat
> version = '0.1.27'
> This program requires python2 
 
### What is taskcat? 
TaskCat is a python Class that helps deploy your cloudformation templates in multiple regions. You can use TaskCat by importing the module and creating a TaskCat object. 

> This repo example code to help you get started.

### Installing taskcat module via pip
```
sudo pip install taskcat
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
# authors:
# tonynv,sancard,sshvans
# License Apaache 2.0
#
# Purpose: This program (tcat) is a caloudformation testing tool
# Tests can defined in a configuration yaml (config.yml)
# @TODO
        # system level configuration (sys will override repo configs)
        # if os.path.isfile(sys_yml):
        # tcat.load_sysymal(sys_yml)

from taskcat import TaskCat
import yaml

def main():
    tcat_obj = TaskCat()
    tcat_obj.welcome('taskcat.io')
    # Initalize cli interface
    # @TODO Add RestFull Interface
    args = tcat_obj.interface
    # Init aws api and set default auth method
    tcat_obj.set_config(args.config_yml)
    # tcat_obj.set_config('ci/config.yml')
    # Get API Handle - Try all know auth
    tcat_obj.aws_api_init(args)

# Run in ymal mode (Batch Test execution)
# --Begin
# Check for valid ymal and required keys in config
    if args.config_yml is not None:
        print "[TSKCAT] : Mode of operation: \t [ymal-mode]"
        print "[TSKCAT] : Configuration yml: \t [%s]" % args.config_yml


        test_list = tcat_obj.validate_yaml(args.config_yml)

# Load ymal into local tcat config
        with open(tcat_obj.get_config(), 'r') as cfg:
            tcat_cfg = yaml.safe_load(cfg.read())
        cfg.close()

        tcat_obj.s3upload(tcat_cfg)
        tcat_obj.validate_template(tcat_cfg, test_list)
        tcat_obj.validate_parameters(tcat_cfg, test_list)
        stackinfo = tcat_obj.stackcreate(tcat_cfg, test_list, 'tonyv')
        tcat_obj.get_stackstatus(stackinfo , 5)

# --End
# Finish run in ymal mode

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
	If you need help you can reach out to via tonynv@amazon.com

*Enjoy!* 
