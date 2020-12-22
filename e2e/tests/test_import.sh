#!/bin/bash -e

EXIT_CODE=0

python -m unittest discover test_imported/ >& /tmp/output || EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]] ; then
    echo '$ python -m unittest discover test_imported/'
    cat /tmp/output
    echo "FAILED: expected exit code to be 0"
    exit 1
fi
