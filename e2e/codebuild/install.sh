#!/bin/bash -e

git clone https://github.com/${PR_GITHUB_ORG}/${PR_REPO_NAME}.git
cd ${PR_REPO_NAME}
git checkout ${PR_BRANCH}
eval "$(pyenv init -)"

for ver in "$@" ; do
    pyenv shell ${ver}
    pip install --upgrade pip > /dev/null 2> /dev/null
    pip install -r ./dev-requirements.txt > /dev/null
    pip install -e . > /dev/null
done
