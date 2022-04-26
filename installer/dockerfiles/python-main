############################################################
# Based on Python3 image
############################################################

FROM python:3
MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=production

# Run as root
USER root

# Set the work directory
WORKDIR /mnt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir  taskcat
