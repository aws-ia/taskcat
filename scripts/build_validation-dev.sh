#!/bin/bash 
# This script validates the development branch of taskcat
set +x
# Add .local/bin to path
export PATH=:~/.local/bin/:$PATH

# Pull latest version
echo "Checking for new docker image taskcat/taskcat-develop:latest"
docker pull taskcat/taskcat-develop

LAST_VERSION=$(cat ~/taskcat-develop-version)
CURRENT_VERSION=$(docker image ls taskcat/taskcat-develop:latest -q)

echo "LAST_VERSION = $LAST_VERSION"
echo "CURRENT_VERSION = $CURRENT_VERSION"

if [ ${LAST_VERSION} != ${CURRENT_VERSION} ]
then
    echo "Validating taskcat/taskcat-develop container"
  cd examples
  taskcat-develop -c sample-taskcat-project/ci/taskcat-autobucket.yml

  echo ${CURRENT_VERSION} >~/taskcat-develop-version
else
    echo "No changes found in taskcat/taskcat-develop:latest"
fi
