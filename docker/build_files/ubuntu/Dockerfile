############################################################
# taskcat Dockerfile
# Based on Ubuntu
############################################################
FROM ubuntu:latest

MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=1.45

# Operating Systems
LABEL container-os: ubuntu

# Run as 
USER root

# Update 
RUN apt-get update -y

# Install basic applications
RUN apt-get install -y git curl 

# Install Python and Basic Python Tools
RUN apt-get install -y python  python-pip

# Clone taskcat
RUN git clone https://github.com/aws-quickstart/taskcat.git

# Build taskcat
RUN cd taskcat && pip install -r requirements.txt && pip install .

# Add taskcat to container path
RUN cd taskcat && cp taskcat_test.py /usr/bin/taskcat

# Set the work directory
WORKDIR /mnt

# Make taskcat executable
RUN chmod 755 /usr/bin/taskcat
