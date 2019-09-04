#!/bin/bash -ex

# pass without any nested stacks
${BIN} lint ../../tests/data/lambda_build_with_submodules/.taskcat.yml >& /tmp/output
cat /tmp/output

if [[ $(cat /tmp/output | grep -c "Lint passed for test mytest on template") -ne 1 ]]
then
    echo "FAILED: expected test mytest to pass"
    exit 1
fi

# pass with 4 descendant templates
${BIN} lint ../../tests/data/nested-fail/ci/taskcat.yml --project-root ../ >& /tmp/output
cat /tmp/output

if [[ $(cat /tmp/output | grep -c "Lint passed for test taskcat-json on template ") -ne 5 ]]
then
    echo "FAILED: expected test taskcat-json to pass and to check all 5 child templates"
    exit 1
fi

# pass with warning
${BIN} lint ../../tests/data/lint-warning/.taskcat.yml  >& /tmp/output
cat /tmp/output

if [[ $(cat /tmp/output | grep -c '\[2001\] \[Check if Parameters are Used\]') -ne 1 ]]
then
    echo "FAILED: expected lint warning"
    exit 1
fi

# fail with error
EXIT_CODE=0
${BIN} lint ../../tests/data/lint-error/.taskcat.yml >& /tmp/output || EXIT_CODE=$?
cat /tmp/output

if [[ ${EXIT_CODE} -ne 1 ]] ; then
    echo "FAILED: expected exit code to be 1"
    exit 1
fi

if [[ $(cat /tmp/output | grep -c "\[3002\] \[Resource properties are valid\]") -ne 1 ]]
then
    echo "FAILED: expected lint error"
    exit 1
fi
