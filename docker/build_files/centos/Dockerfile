############################################################
# taskcat Dockerfile
# Based on Centos
############################################################

FROM centos:latest
MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=1.45

# Operating Systems
LABEL container-os: centos

# Run as root
USER root

# Install epel
RUN yum -y install epel-release && yum clean all

# Update 
RUN yum update -y

# Install basic applications
RUN yum install -y curl 

# Install Python and Basic Python Tools
RUN yum install -y  python python34-pip python-devel gcc
RUN unlink /usr/bin/python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Clone taskcat
RUN pip3 install taskcat 

RUN curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/master/taskcat_test.py  -o /usr/local/bin/taskcat

# Set the work directory
WORKDIR /mnt

# Make taskcat executable
RUN chmod 755 /usr/local/bin/taskcat

# Remove source
RUN rm -rf taskcat 
