#!/bin/bash -e

EXIT_CODE=0
PROJECT_ROOT='../../tests/data/stackurlhelper/badtemplateurl'

PYTHONIOENCODING=UTF-8 ${BIN} -d lint -p ${PROJECT_ROOT}  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat lint -p ./tests/data/stackurlhelper/badtemplateurl'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

rm -rf ${PROJECT_ROOT}/taskcat_outputs
