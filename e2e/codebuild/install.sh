#!/bin/bash -e

git clone https://github.com/${PR_GITHUB_ORG}/${PR_REPO_NAME}.git
cd ${PR_REPO_NAME}
git merge --no-edit ${PR_BRANCH}
eval "$(pyenv init -)"

for ver in "$@" ; do
    pyenv shell ${ver}
    pip install --upgrade pip > /dev/null 2> /dev/null
    pip install -r ./dev-requirements.txt > /dev/null
    pip install wheel  > /dev/null
    rm -rf ./dist/
    python setup.py sdist bdist_wheel  > /dev/null
    pip install ./dist/taskcat-*.tar.gz > /dev/null
done
