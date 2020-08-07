FROM python:3-alpine
MAINTAINER "Tony Vattathil" tonynv@amazon.com

# Version
LABEL version=production

# Operating Systems
LABEL container-os=alpine
RUN apk add --no-cache --virtual .build-deps gcc musl-dev
RUN pip3 install taskcat --upgrade

# Set the work directory
WORKDIR /mnt
