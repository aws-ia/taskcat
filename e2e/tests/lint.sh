#!/bin/bash -ex

# pass without any nested stacks
${BIN} lint -p ../../tests/data/lambda_build_with_submodules >& /tmp/output
cat /tmp/output

if [[ $(cat /tmp/output | grep -c "Lint passed for test mytest on template") -ne 1 ]]
then
    echo "FAILED: expected test mytest to pass"
    exit 1
fi

# pass with 4 descendant templates
${BIN} lint -p ../../tests/data/nested-fail >& /tmp/output
cat /tmp/output

if [[ $(cat /tmp/output | grep -c "Lint passed for test taskcat-json on template ") -ne 5 ]]
then
    echo "FAILED: expected test taskcat-json to pass and to check all 5 child templates"
    exit 1
fi

# pass with warning
${BIN} lint -p ../../tests/data/lint-warning  >& /tmp/output
cat /tmp/output

if [[ $(cat /tmp/output | grep -c '\[2001\] \[Check if Parameters are Used\]') -ne 1 ]]
then
    echo "FAILED: expected lint warning"
    exit 1
fi

# fail with error
EXIT_CODE=0
${BIN} lint -p ../../tests/data/lint-error >& /tmp/output || EXIT_CODE=$?
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
