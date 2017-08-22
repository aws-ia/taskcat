############################################################
# taskcat Dockerfile
# Based on Fedora
############################################################

FROM fedora:latest
MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=development 

# Operating Systems
LABEL container-os: fedora

# Run as root
USER root

RUN dnf install git -y
# Install taskcat (develop)
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip3 install boto3 pyfiglet pyyaml tabulate yattag
RUN pip3 install -i https://testpypi.python.org/pypi taskcat  --upgrade

ADD https://raw.githubusercontent.com/aws-quickstart/taskcat/develop/taskcat.py /usr/local/bin/taskcat
ADD https://raw.githubusercontent.com/aws-quickstart/taskcat/develop/alchemist.py /usr/local/bin/alchemist

# Set the work directory
WORKDIR /mnt

# Make taskcat executable
RUN chmod 755 /usr/local/bin/taskcat
RUN chmod 755 /usr/local/bin/alchemist
