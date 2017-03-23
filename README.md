
# taskcat
> version = '0.1.40'
> This program requires python2 

# Currently in beta release

 
### What is taskcat? 
TaskCat is a python Class that helps deploy your cloudformation templates in multiple regions. You can use TaskCat by importing the module and creating a TaskCat object. 

### Setting up Test Cases 
To setup taskcat test tests is a two step process:
* Step 1 Define your test in the config.ymal
* Step 2 Build a json input file for your cloudformation template.

#### Step 1 Creating a config.ymal
You can generate a sample config.ymal by running `./taskcat.py -ey`
The followup's command will create a sample config.ymal
```
./taskcat.py -ey | egrep -v '#|^$'  >config.ymal
```
Open the file with and editor and update the filenames to match your need. (See section on working with the ymal file)

#### Step 2 Building a json input file
The example below shows an input file for a stack that requires two parameters `KeyPair` and `InstanceType`
json

    [{
    	"ParameterKey": "KeyPair",
    	"ParameterValue": "mykey"
    }, {
    	"ParameterKey": "InstanceType",
    	"ParameterValue": "t2.small"
    }]

## Installing taskcat

### Installing taskcat (Option 1)
> Prerequisites: Python 2.7 and pip

    curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/master/pip-install | sudo python -E

### Installing taskcat via docker (Option 2)
> Prerequisites: docker

    curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/master/docker-install | sudo python -E


### Run taskcat 
    docker run -v $(pwd):/mnt -it taskcat/taskcat taskcat -h

Note: (If you do not have root privileges taskcat will install in the current directory)
