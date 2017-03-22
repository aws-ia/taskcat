############################################################
# taskcat Dockerfile
# Based on Centos
############################################################

MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=1.38

# Operating Systems
LABEL container-os: centos
FROM centos:latest


# Run as root
USER root

# Install epel
RUN yum -y install epel-release && yum clean all

# Update 
RUN yum update -y

# Install basic applications
RUN yum  install -y git curl 

# Install Python and Basic Python Tools
RUN yum install -y python python-pip python-devel gcc

# Clone taskcat
RUN git clone https://github.com/aws-quickstart/taskcat.git

# Build taskcat from git master
RUN cd taskcat && pip install -r requirements.txt && pip install .

# Add taskcat to container path
RUN cp taskcat_test.py /usr/bin/taskcat

# Set the work directory
WORKDIR /mnt

# Make taskcat executable
RUN chmod 755 /usr/bin/taskcat