#!/bin/bash -e

EXIT_CODE=0

${BIN} -d --help  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

${BIN} -d -h  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat-v9 -d -h'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

${BIN} -d package --help  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat-v9 -d package --help'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

${BIN} -d lint -h  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat-v9 -d lint -h'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

${BIN}  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat-v9'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi
