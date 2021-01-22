#!/bin/bash -e

SOURCE="../../taskcat/"
OMIT="../../taskcat/_stacker.py"
COV_CMD="coverage run -a --source ${SOURCE} --omit ${OMIT}"
BIN="../../bin/taskcat"

eval "$(pyenv init -)"
cd e2e/tests/

if [[ -f .coverage ]] ; then rm .coverage ; fi

FAILED=0

function failed() {
    FAILED=1
    echo "TEST FAILED: ${t} python version: ${ver}"
}

for ver in "$@" ; do
    pyenv shell ${ver}
    echo "running tests using ${ver}..."
    for t in $(ls -1 *.sh) ; do
        chmod +x ./${t}
        echo "  running tests in ${t}..."
        BIN=${BIN} COV_CMD=${COV_CMD} ./${t} || failed
    done
done

coverage report > ../../cov_report

pyenv shell 3.7.4
if [[ ${FAILED} -eq 0 ]] ; then
  echo "ALL TESTS PASSED"
else
  echo "TEST FAILED"
fi
if [[ "${LOCAL_TEST}" != "True" ]]; then
  python /results_comment.py "$(git rev-parse HEAD)" ${FAILED}
fi
exit ${FAILED}
