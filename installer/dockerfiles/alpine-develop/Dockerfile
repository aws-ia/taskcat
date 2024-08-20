FROM public.ecr.aws/docker/library/python:3.12.5-alpine3.20

LABEL maintainer="Tony Vattathil tonynv@amazon.com"

# Version
LABEL version=production

# Operating Systems
LABEL container-os=python

RUN apk update && apt install -y gcc
RUN pip3 install taskcat --upgrade \
&& pip3 install --index-url https://test.pypi.org/simple/ taskcat  --no-cache-dir --force --upgrade --no-deps

# Set the work directory
WORKDIR /mnt
