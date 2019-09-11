#!/bin/bash -ex

# pass on CREATE_COMPLETE
${BIN} test ../../tests/data/nested-create/ci/taskcat.yml -p ../../tests/data/nested-create >& /tmp/output
cat /tmp/output

if [[ $(cat /tmp/output | grep -c "taskcat e2e passs for module (test)") -ne 1 ]]
then
    echo "FAILED: expected ec2 tests to pass"
    exit 1
fi

# fail with error on CREATE_FAIL
# TODO: not implemented
