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
RUN /usr/local/bin/pip3 install boto3 pyfiglet pyyaml tabulate yattag
RUN /usr/local/bin/pip3 install -i https://test.pypi.org/pypi taskcat  --upgrade

# Set the work directory
WORKDIR /mnt

# Make taskcat executable
RUN chmod 755 /usr/local/bin/taskcat
RUN chmod 755 /usr/local/bin/alchemist
