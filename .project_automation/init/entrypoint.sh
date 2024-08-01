#!/bin/bash -e

## NOTE: paths may differ when running in a managed task. To ensure behavior is consistent between
# managed and local tasks always use these variables for the project and project type path
PROJECT_PATH=${BASE_PATH}/project
PROJECT_TYPE_PATH=${BASE_PATH}/projecttype

echo "running copier"
cd "${PROJECT_PATH}"
copier copy --defaults -f "${PROJECT_TYPE_PATH}" .

if [ -n "${BASE_PATH}" ]
then
  echo "committing results and pushing to repo"
  git add .
  git commit -m "initial commit"
  git push --force
else
  echo "Local build mode (skipping git commit)"
fi
