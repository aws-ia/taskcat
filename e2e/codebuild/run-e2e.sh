#!/bin/bash -ex

SOURCE="../../taskcat/"
OMIT="../../taskcat/_stacker.py"
CMD="coverage run -a --source ${SOURCE} --omit ${OMIT} ../../bin/taskcat-v9"

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
    for t in $(ls -1 *.sh) ; do
        chmod +x ./${t}
        BIN=${CMD} ./${t} || failed
    done
done

coverage report > ../../cov_report

pyenv shell 3.7.4
python /results_comment.py $(git rev-parse HEAD) ${FAILED}
exit ${FAILED}
