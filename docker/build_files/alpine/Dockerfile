############################################################
# taskcat Dockerfile
# Based on alpine
############################################################
FROM alpine
MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=1.46

# Operating Systems
LABEL container-os: alpine

ENV PACKAGES="\
  dumb-init \
  musl \
  linux-headers \
  build-base \
  bash \
  gcc \
  git \
  ca-certificates \
  python2 \
  python2-dev \
  py-setuptools \
"

RUN echo \

  # Add the packages, with a CDN-breakage fallback if needed
  && apk add --no-cache $PACKAGES || \
    (sed -i -e 's/dl-cdn/dl-4/g' /etc/apk/repositories && apk add --no-cache $PACKAGES) \

  # make some useful symlinks that are expected to exist
  && if [[ ! -e /usr/bin/python ]];        then ln -sf /usr/bin/python2.7 /usr/bin/python; fi \
  && if [[ ! -e /usr/bin/python-config ]]; then ln -sf /usr/bin/python2.7-config /usr/bin/python-config; fi \
  && if [[ ! -e /usr/bin/easy_install ]];  then ln -sf /usr/bin/easy_install-2.7 /usr/bin/easy_install; fi \

  # Install and upgrade Pip
  && easy_install pip \
  && pip install --upgrade pip \
  && if [[ ! -e /usr/bin/pip ]]; then ln -sf /usr/bin/pip2.7 /usr/bin/pip; fi \
  && echo

# Run as root
USER root

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
