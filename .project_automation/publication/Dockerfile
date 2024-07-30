FROM public.ecr.aws/codebuild/amazonlinux2-x86_64-standard:4.0
RUN yum install -y yum-utils && yum-config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo && yum install -y gh
RUN pip install copier
RUN pip install bump2version
