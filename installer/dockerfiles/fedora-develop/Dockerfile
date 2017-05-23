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

# Install taskcat (develop)
RUN pip3 install --extra-index-url https://testpypi.python.org/pypi taskcat  --upgrade

ADD https://raw.githubusercontent.com/aws-quickstart/taskcat/develop/taskcat_test.py /usr/local/bin/taskcat

# Set the work directory
WORKDIR /mnt

# Make taskcat executable
RUN chmod 755 /usr/local/bin/taskcat
