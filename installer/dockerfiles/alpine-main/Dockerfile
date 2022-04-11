FROM python:3-alpine
LABEL maintainer="Tony Vattathil tonynv@amazon.com"

# Version
LABEL version=production

# Operating Systems
LABEL container-os=alpine
RUN apk update && apk add python3-dev gcc libc-dev

#RUN pip3 install taskcat
RUN pip3 install taskcat --upgrade


# Set the work directory
WORKDIR /mnt
