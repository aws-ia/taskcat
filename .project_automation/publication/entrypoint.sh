#!/bin/bash -x

## NOTE: paths may differ when running in a managed task. To ensure behavior is consistent between
# managed and local tasks always use these variables for the project and project type path
PROJECT_PATH=${BASE_PATH}/project
PROJECT_TYPE_PATH=${BASE_PATH}/projecttype

cd ${PROJECT_PATH}

pip install poetry

LAST_COMMIT_MESSAGE=$(git log --format=%B -n 1 | head -n 1)
set +x
poetry config pypi-token.pypi $(aws --region us-west-2 secretsmanager get-secret-value --secret-id pypi --query SecretString --output text)
set -x

function new_release(){
  LAST_RELEASE_COMMIT=$(git rev-list --tags --max-count=1)
  TAG_BODY=$(git --no-pager log --no-merges --oneline ${LAST_RELEASE_COMMIT}..HEAD  --pretty='- %h %s')
  VERSION=$(poetry version | awk '{print $2}')
  git tag -a "${VERSION}" -m "${TAG_BODY}"
  git push --tags
}

update_release_branch(){
  poetry version patch
  VERSION=$(poetry version | awk '{print $2}')
  git add pyproject.toml
  git commit -m "Release: v${VERSION}"
  git push origin main:release/v0.x --force
}

function _pypi_release(){
  poetry publish --build -r test-pypi
}

set +e
echo ${LAST_COMMIT_MESSAGE} | egrep -i "Merge pull request.*from aws-ia/release.*$"; EC=$?
set -e
if [[ $EC -eq 0 ]]; then
  new_release
  _pypi_release
else
  update_release_branch
fi
