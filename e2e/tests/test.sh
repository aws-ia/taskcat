#!/bin/bash -e

EXIT_CODE=0
PROJECT_ROOT='../../tests/data/nested-create'

${BIN} test run -p ${PROJECT_ROOT}  >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ taskcat test -p ./tests/data/nested-create'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi

rm -rf ${PROJECT_ROOT}/taskcat_outputs

