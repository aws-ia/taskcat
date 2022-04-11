FROM python:3-alpine
LABEL maintainer="Tony Vattathil tonynv@amazon.com"

# Version
LABEL version=production

# Operating Systems
LABEL container-os=alpine

RUN apk update && apk add python3-dev gcc libc-dev
RUN pip3 install taskcat --upgrade \
&& pip3 install --index-url https://test.pypi.org/simple/ taskcat  --no-cache-dir --force --upgrade --no-deps

# Set the work directory
WORKDIR /mnt
