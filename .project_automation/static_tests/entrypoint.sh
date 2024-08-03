#!/bin/bash -ex

## NOTE: paths may differ when running in a managed task. To ensure behavior is consistent between
# managed and local tasks always use these variables for the project and project type path
PROJECT_PATH=${BASE_PATH}/project
PROJECT_TYPE_PATH=${BASE_PATH}/projecttype
cd $(mktemp -d)
git clone https://github.com/awslabs/git-secrets.git
cd git-secrets
make install
cd ${PROJECT_PATH}
pip install -r dev-requirements.txt  -r requirements.txt
pre-commit run --all-files
