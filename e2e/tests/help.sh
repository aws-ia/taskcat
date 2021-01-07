#!/bin/bash -e

EXIT_CODE=0

${COV_CMD} ${BIN} -d --help  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

${COV_CMD} ${BIN} -d -h  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat -d -h'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

${COV_CMD} ${BIN} -d package --help  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat -d package --help'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

${COV_CMD} ${BIN} -d lint -h  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat -d lint -h'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

${COV_CMD} ${BIN}  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi
