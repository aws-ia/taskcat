############################################################
# taskcat Dockerfile
# Based on Centos
############################################################

FROM centos:latest
MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=1.70

# Operating Systems
LABEL container-os: centos

# Run as root
USER root

# Install epel, Update, Install basic applications,  Install Python and Basic Python Tools
RUN yum clean all && \
    yum -y install epel-release && \
    yum update -y && \
    yum install -y curl && \
    yum install -y python python34-pip python-devel gcc && \
    yum clean all
    
RUN unlink /usr/bin/python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Clone taskcat
RUN pip3 install taskcat 

ADD https://raw.githubusercontent.com/aws-quickstart/taskcat/master/taskcat_test.py /usr/local/bin/taskcat

# Set the work directory
WORKDIR /mnt

# Make taskcat executable
RUN chmod 755 /usr/local/bin/taskcat
