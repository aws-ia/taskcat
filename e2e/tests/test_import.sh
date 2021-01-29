#!/bin/bash -e

EXIT_CODE=0
SOURCE="../../taskcat/"
OMIT="../../taskcat/_stacker.py"
COV_CMD="coverage run -a --source ${SOURCE} --omit ${OMIT}"

${COV_CMD} -m unittest discover test_imported/ >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ python -m unittest discover test_imported/'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi
