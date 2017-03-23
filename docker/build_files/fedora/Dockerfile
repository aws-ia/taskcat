############################################################
# taskcat Dockerfile
# Based on Fedora
############################################################

FROM fedora:latest
MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=1.40

# Operating Systems
LABEL container-os: fedora

# Run as root
USER root

# Install epel

# Install basic applications
RUN dnf update -y
RUN dnf install -y git curl 

# Install Python and Basic Python Tools
RUN dnf install -y python python-pip python-devel gcc

# Clone taskcat
RUN git clone https://github.com/aws-quickstart/taskcat.git

# Build taskcat from git master
RUN cd taskcat && pip install -r requirements.txt && pip install .

# Add taskcat to container path
RUN cd taskcat && cp taskcat_test.py /usr/bin/taskcat

# Set the work directory
WORKDIR /mnt

# Make taskcat executable
RUN chmod 755 /usr/bin/taskcat

# Remove source
RUN rm -rf taskcat 

# Clean dnf cache
RUN dnf clean all

