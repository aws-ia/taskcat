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
RUN pip3 install --upgrade pip
RUN ln -s /usr/local/bin/pip /usr/bin/pip
RUN git clone -b develop https://github.com/aws-quickstart/taskcat.git 
WORKDIR taskcat
RUN curl -s https://raw.githubusercontent.com/aws-quickstart/taskcat/develop/scripts/build_develop.sh -O
RUN bash -xe build_develop.sh
RUN python3 setup.py build
RUN python3 setup.py install --user
RUN cp -rf ~/.local/bin/* /usr/local/bin

# Make taskcat executable
RUN chmod 755 /usr/local/bin/*

# Set the work directory
WORKDIR /mnt
