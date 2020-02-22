FROM python:3.8-slim

RUN pip install taskcat

ENTRYPOINT ["taskcat"]
CMD ["--help"]
