#/bin/bash -x
# Get pip creds (in ecr)

# Create taskcat
cp taskcat.py bin/taskcat

# Create alchemist
cp alchemist.py bin/taskcat-alchemist
cp alchemist.py bin/alchemist

# Stage Stub
cp scripts/setup_stub-develop.py ./setup_stub-develop.py
# Update Pip Version
python3 -c 'import datetime; print (open("./setup_stub-develop.py").read().replace("VERSION_STUB",datetime.datetime.now().strftime("%Y.%m%d.%H%M%S")+".dev0"))' >setup.py
