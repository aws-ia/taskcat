
# taskcat
> version = '0.1.50'
> This program requires python3 

# Currently in beta release
Please report bugs here https://github.com/aws-quickstart/taskcat/issues
 
## What is taskcat? 
taskcat is a python Class that helps deploy your cloudformation templates in multiple regions. You can use taskcat by importing the module and creating a taskcat object. 

## Setting up Test Cases 
* Step 1 Define your test in the config.yml
* Step 2 Build a json input file for your cloudformation template.

### Step 1 Creating a config.ymal
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
      senario-1:
        parameter_input: sample-cloudformation-input.json
        regions:
          - us-west-1
          - us-east-1
        template_file: sample-cloudformation-project-withvpc.template
      # The following test will test in both all 4 region defined in the global region section using sample-cloudformation-input.json as inputs
          senario-all-regions:
        parameter_input: sample-cloudformation-input.jsonon
        template_file: sample-cloudformation-project-withvpc.template

#### Example of project directory structure
    sample-cloudformation-project/
    ├── LICENSE.txt
    ├── README.md
    ├── ci
    │   └── config.yml <- This the config file that will hold all the test definitions 
    │   └──  sample-cloudformation-input.json <-  This file contain input that will pass in during stack creation (See auto parms for more info)
        ├── scripts
        │   └── userdata.sh <- If you have userdata scripts you can load then in the scripts directory
        ├── submodules  <- If you have git submodules you can load them in the submodules directory
        │   └── quickstart-aws-vpc
        │       └── templates
        │           └── aws-vpc.template
        └── templates
            ├── sample-cloudformation-project-novpc.template 
            └── sample-cloudformation-project-withvpc.template <- Second version on template that will create a vpc with the worklo    ad 


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
 * X is lengeth of the string

(Optionally - you can specify the type of password by adding A or S)

 * A aplha-numeric passwords
 * S passwords with special characters

> Example: $[taskcat_genpass_8A]
> Generates: `tI8zN3iX8`
> Example: $[taskcat_genpass_8S]
> Generates: mA5@cB5!

### (Availablity Zones)
Value that matches the following pattern will be replaced

* Parameters must start with $[
* Parameters must end with ]
* genaz in invoked when _genaz_X is found
* A number of AZ's will be selected from the region the stack is attempting to launch

> Example: $[taskcat_genaz_2]  
> Generates: us-east-1a, us-east-2b
> (if the region is us-east-1)

## Installing taskcat

### Installing taskcat (Option 1)
> Prerequisites: Python 2.7 and pip

    curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/master/pip-install | python -E

### Installing taskcat via docker (Option 2) 
> Prerequisites: docker

    curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/master/docker-install | sudo python -E

> Note: (If you do not have root privileges taskcat will install in the current directory)

### Run taskcat

If you have AWS credentials sourced 
    
     taskcat -c sample-cloudformation-project/ci/config.yml


If you need to pass ACCESS and SECRET keys

    taskcat -c sample-cloudformation-project/ci/config.yml -A YOUR_ACCESS_KEY -S YOUR_SECRET_KEY

If you want to use a different account or profile

    taskcat -c sample-cloudformation-project/ci/config.yml -P boto-profile-name

