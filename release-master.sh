#!/bin/bash
#This script build a new version of taskcat
./build-tools/new-master-version.sh ./setup.py
./build-tools/new-master-version.sh ./taskcat/taskcat.py
./build-tools/new-master-version.sh ./README.md
./build-tools/new-master-version.sh ./docker/build_files/centos/Dockerfile 
./build-tools/new-master-version.sh ./docker/build_files/build_image.sh 

VERSION=$(grep version taskcat/taskcat.py |head -1 | awk -F'=|,' '{print $2}' | sed -e s/\'//|tr -d " "|tr -d "'")
echo $VERSION
python setup.py sdist 
#twine  register $(/bin/ls -1 dist/)
#python setup.py bdist_wheel 
python -m mkdocs gh-deploy --clean  
#python setup.py upload_docs --upload-dir=site

git tag $VERSION
git push --tags origin develop
git commit -m "release $VERSION"

twine upload dist/*

rm -rf  dist/*
rm  -rf build/*

cp ./setup.py ./setup-develop.py

VERSION=$(grep version taskcat/taskcat.py |head -1 | awk -F'=|,' '{print $2}' | sed -e s/\'//|tr -d " "|tr -d "'")
echo "Current Version is $VERSION"
DEV_VERSION=${VERSION}.dev1

echo "Syncing version $DEV_VERSION to setup-develop.py":
sed -i '' -e "s/${VERSION}/${DEV_VERSION}/" setup-develop.py
