FROM python:3.8.16-alpine3.17

LABEL maintainer="Tony Vattathil tonynv@amazon.com"

# Version
LABEL version=production

# Operating Systems
LABEL container-os=python

RUN apk update && apk add python3-dev gcc libc-dev go bash git
#RUN pip3 install --no-cache-dir taskcat
RUN python3 -m pip install -e git+https://github.com/aws-ia/taskcat.git#egg=taskcat

# Set the work directory
WORKDIR /mnt
