FROM public.ecr.aws/codebuild/amazonlinux2-x86_64-standard:4.0

RUN yum update -y &&\
    yum install -y yum-utils
RUN yum-config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo && \
    yum install -y gh
RUN pip3 install copier
