#!/bin/bash -ex

git clone https://github.com/${PR_GITHUB_ORG}/${PR_REPO_NAME}.git
cd ${PR_REPO_NAME}
git checkout ${PR_BRANCH}
eval "$(pyenv init -)"

for ver in "$@" ; do
    pyenv shell ${ver}
    $(pyenv which pip) install --upgrade pip > /dev/null 2> /dev/null
    $(pyenv which pip) install -r ./dev-requirements.txt > /dev/null
    $(pyenv which pip) install -e . > /dev/null
done
