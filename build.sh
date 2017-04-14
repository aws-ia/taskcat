#!/bin/bash
#This script build a new version of taskcat
./build-tools/newversion.sh ./setup.py
./build-tools/newversion.sh ./taskcat/taskcat.py
./build-tools/newversion.sh ./README.md
./build-tools/newversion.sh ./docker/build_files/centos/Dockerfile 
./build-tools/newversion.sh ./docker/build_files/build_image.sh 

VERSION=$(grep version taskcat/taskcat.py |head -1 | awk -F'=|,' '{print $2}' | sed -e s/\'//|tr -d " "|tr -d "'")
echo $VERSION
python setup.py sdist 
#twine  register $(/bin/ls -1 dist/)
#python setup.py bdist_wheel 
python -m mkdocs gh-deploy --clean  
#python setup.py upload_docs --upload-dir=site

git tag $VERSION
git push --tags origin master
git commit -m "release $VERSION"

twine upload dist/*

rm -rf  dist/*
rm  -rf build/*
