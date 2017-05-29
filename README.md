
# TaskCat
> version = '2017.0528.220651'
> This program requires python3 

# Currently in beta release
Please report bugs here https://github.com/aws-quickstart/taskcat/issues
 
## What is TaskCat? 
TaskCat is a tool that tests AWS CloudFormation templates. It deploys your AWS CloudFormation template in multiple AWS Regions and generates a report with a pass/fail grade for each region. You can specify the regions and number of Availability Zones you want to include in the test, and pass in parameter values from your AWS CloudFormation template. TaskCat is implemented as a Python class that you import, instantiate, and run.
 
TestCat was developed by the AWS Quick Start team to test AWS CloudFormation templates that automatically deploy workloads on AWS. We’re pleased to make the tool available to all developers who want to validate their custom AWS CloudFormation 
templates across AWS Regions

## Files you’ll need
* **config.yml** - This file contains the test cases
* **JSON input** - This file contains the inputs that you want to pass to AWS CloudFormation template that is being tested

* Step 1 Building your configuration file 
* Step 2 Building your JSON input file.

#### Step 1 Creating a config.ymal
You can generate a sample config.ymal by running `taskcat -ey`
The followup's command will create a sample config.yml
```
./taskcat -ey | egrep -v '#|^$'  >config.yml
```
Open the config.yml file with and editor and update the filenames to match your need. 

#### Example of config.yml 
    global:
      owner: owner@company.com
      project: sample-cloudformation-project <- Must match the root directory of project (usually the name of git repo)
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
    └── ci
       ├── config.yml <- This the config file that will hold all the test definitions 
       ├──  sample-cloudformation-input-novpc.json <-  This file contain input that will pass in during stack creation [vpc version] (See auto parms for more info)
       ├──  sample-cloudformation-input-withvpc.json <-  This file contain input that will pass in during stack creation [no-vpc version](See auto parms for more info)
       ├── scripts
       │   └── userdata.sh <- If you have userdata scripts you can load then in the scripts directory
       ├── submodules  <- If you have git submodules you can load them in the submodules directory
       │   └── quickstart-aws-vpc
       │       └── templates
       │           └── aws-vpc.template
       └── templates
           ├── sample-cloudformation-project-novpc.template 
           └── sample-cloudformation-project-withvpc.template <- Second version on template that will create a vpc with the workload 


### Step 2 Building a json input file
The example below shows an input file for a stack that requires four parameters `KeyPair`,`InstanceType`, `AvailablityZones` and `Password`

Note: you can auto generate values at runtime using special tokens (see example below).
> The following json will evaluate

#### From:

    [
        {
    	"ParameterKey": "KeyPair",
    	"ParameterValue": "mykey"
        }, 
        {
    	"ParameterKey": "InstanceType",
    	"ParameterValue": "t2.small"
        }
        {
        "ParameterKey": "AvailablityZones",
        "ParameterValue": "$[taskcat_genaz_2]" 
        }, 
        {
        "ParameterKey": "Password",
        "ParameterValue": "$[taskcat_genpass_8A]"
        }, 
    ]


#### To:

    [
        {
        "ParameterKey": "KeyPair",
        "ParameterValue": "mykey"
        }, 
        {
        "ParameterKey": "InstanceType",
        "ParameterValue": "t2.small"
        }
        {
        "ParameterKey": "AvailablityZones",
        "ParameterValue": "us-east-1a, us-east1b" 
        }, 
        {
        "ParameterKey": "Password",
        "ParameterValue": "tI8zN3iX8"
        }, 
    ]


#### More information on Auto-generated stack inputs

### (Passwords)
Value that matches the following pattern will be replaced

 * Parameters must start with $[
 * Parameters must end with ]
 * genpass in invoked when _genpass_X is found
 * X is length of the string

(Optionally - you can specify the type of password by adding A or S)

 * A alpha-numeric passwords
 * S passwords with special characters

> Example: $[taskcat_genpass_8A]
> Generates: `tI8zN3iX8`
> Example: $[taskcat_genpass_8S]
> Generates: mA5@cB5!

### (Availability Zones)
Value that matches the following pattern will be replaced

* Parameters must start with $[
* Parameters must end with ]
* genaz in invoked when _genaz_X is found
* A number of AZ's will be selected from the region the stack is attempting to launch

> Example: $[taskcat_genaz_2]  
> Generates: us-east-1a, us-east-2b
> (if the region is us-east-1)

## Installing TaskCat

### Installing TaskCat (Option 1)
> Prerequisites: Python 3.5+ and pip3
```
curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/master/installer/pip/pip3-install-master| python -E
```
### Installing TaskCat via docker (Option 2) 
> Prerequisites: docker
```
curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/master/installer/docker-install-master| sudo python -E
```
> Note: (If you do not have root privileges taskcat will install in the current directory)

### Running TaskCat

If you have AWS credentials sourced 
```
taskcat -c sample-cloudformation-project/ci/config.yml
```
If you need to pass ACCESS and SECRET keys
```
taskcat -c sample-cloudformation-project/ci/config.yml -A YOUR_ACCESS_KEY -S YOUR_SECRET_KEY
```
If you want to use a different account or profile
```
taskcat -c sample-cloudformation-project/ci/config.yml -P boto-profile-name
```
