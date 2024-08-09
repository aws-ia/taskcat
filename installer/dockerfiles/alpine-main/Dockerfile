FROM public.ecr.aws/docker/library/python:3.12.5-alpine3.20

LABEL maintainer="Tony Vattathil tonynv@amazon.com"

# Version
LABEL version=production

# Operating Systems
LABEL container-os=python

RUN apk update && apk add python3-dev gcc libc-dev go bash
RUN python3 -m pip install --upgrade pip
RUN pip3 install --no-cache-dir taskcat


# Set the work directory
WORKDIR /mnt
