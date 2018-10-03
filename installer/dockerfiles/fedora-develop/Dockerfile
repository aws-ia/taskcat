############################################################
# taskcat development Dockerfile
# Based on Fedora
############################################################

FROM fedora:latest
MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=development

# Operating Systems
LABEL container-os=fedora

# Run as root
USER root

RUN dnf install git -y
# Install taskcat (develop)
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip3 install --upgrade pip
RUN ln -s /usr/local/bin/pip /usr/bin/pip
RUN pip install taskcat
RUN pip install --index-url https://test.pypi.org/simple/ taskcat  --no-cache-dir --force --upgrade --no-deps


# Set the work directory
WORKDIR /mnt
