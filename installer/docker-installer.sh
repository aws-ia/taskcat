#!/bin/sh
# authors:
# Tony Vattathil tonynv@amazon.com
# License: Apache 2.0

set -e

echo "[INITIALIZING taskcat installer!!]"

INSTALL_DIR="/usr/local/bin"
DOCKER_IMAGE_TAG="latest"

if [ $# -eq 1 ]; then
    if [ "${1}" = "--develop" ]; then
        DOCKER_IMAGE_TAG="develop"
        BINARY_SUFFIX="-develop"
    else
        echo "Usage: ${0} [--develop]"
        exit 1
    fi
fi

DOCKER_IMAGE=taskcat/taskcat:${DOCKER_IMAGE_TAG}
TASKCAT_BINARY="taskcat${BINARY_SUFFIX}"
ALCHEMIST_BINARY="alchemist${BINARY_SUFFIX}"

if [ -d "${HOME}"/.aws ]; then
    echo "[INFO] : Found boto profile)"
    echo "[INFO] : Boto profile will map to container during execution"
    echo "echo \"[dockerize]\"" > taskcat.docker
    echo "docker run -it --rm -v ${HOME}/.aws:/root/.aws -v \$(pwd):/mnt ${DOCKER_IMAGE} taskcat \$@" >> taskcat.docker
    echo "docker run -it --rm -v ${HOME}/.aws:/root/.aws -v \$(pwd):/mnt ${DOCKER_IMAGE} alchemist \$@" >> alchemist.docker
else
    echo "echo [dockerize]" > taskcat.docker
    echo "echo [dockerize]" > alchemist.docker
    echo "docker run -it --rm -v \$(pwd):/mnt ${DOCKER_IMAGE} taskcat \$@" >> taskcat.docker
    echo "docker run -it --rm -v \$(pwd):/mnt ${DOCKER_IMAGE} alchemist \$@" >> alchemist.docker
fi

if [ "$(id -u)" -eq 0  ];then
    docker pull ${DOCKER_IMAGE}
    mv taskcat.docker ${INSTALL_DIR}/${TASKCAT_BINARY}
    mv alchemist.docker ${INSTALL_DIR}/${ALCHEMIST_BINARY}
    chmod 755 ${INSTALL_DIR}/${TASKCAT_BINARY}
    chmod 755 ${INSTALL_DIR}/${ALCHEMIST_BINARY}
    echo ""
    echo "\t[i] INSTALL COMPLETE"
    echo "\t[i] tools are installed in => ${INSTALL_DIR}"
else
    docker pull ${DOCKER_IMAGE}
    mv taskcat.docker ${TASKCAT_BINARY}
    mv alchemist.docker ${ALCHEMIST_BINARY}
    chmod 755 ${TASKCAT_BINARY}
    chmod 755 ${ALCHEMIST_BINARY}
    echo ""
    echo "\t[i] INSTALL COMPLETE"
    echo "\t[i] Root privileges were not provided!"
    echo "\t[i] Tools are installed in => $(pwd)"
    echo "\t[i] Please add these tools to your path"
    echo "\t[i] sudo mv ${TASKCAT_BINARY} ${INSTALL_DIR}/${TASKCAT_BINARY} ${INSTALL_DIR}"
    echo "\t[i] sudo mv ${ALCHEMIST_BINARY} ${INSTALL_DIR}/${ALCHEMIST_BINARY} ${INSTALL_DIR}"
    echo "\t[i] or run them from this directory with ./${TASKCAT_BINARY} or ./${ALCHEMIST_BINARY}"
fi

echo "\t[i] To run taskcat the program type ${TASKCAT_BINARY}"
echo "\t[i] To run alchemist the program type ${ALCHEMIST_BINARY}"

echo ""
echo "Ready!!"
