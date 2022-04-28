FROM python:3.9.12-alpine3.15

LABEL maintainer="Tony Vattathil tonynv@amazon.com"

# Version
LABEL version=production

# Operating Systems
LABEL container-os=python

#RUN apk update && apk add python3-dev gcc libc-dev
#RUN apt update && apt install -y libpq-dev gcc python3-dev python3-pip
RUN apt update && apt install -y gcc
#RUN pip3 install taskcat
RUN pip3 install --no-cache-dir taskcat


# Set the work directory
WORKDIR /mnt
