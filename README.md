# taskcat
### What is taskcat.io
TaskCat is a python Class that help you test your cloudformation templates in multiple regions. You can use TaskCat by importing the module and creating a TaskCat object. This repo all the code you need to run taskcat

### Installing requirements
    pip install -r requirements.txt in your shell

### Setting up Test Cases 
To setup taskcat test tests is a two step process:
* Step 1 Define your test in the config.ymal
* Step 2 Build a json input file for your cloudformation template.

#### Step 1 Creating a config.ymal
You can generate a sample config.ymal by running `./tcat.py -ey`
The followung command will create a sample config.ymal
   ./tcat.py -ey | egrep -v '#|^$'  >config.ymal
Open the file with and editor and update the filenames to match your need. (See section on working with the ymal file)

#### Step 2 Building a json input file
