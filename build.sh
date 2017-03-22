#!/bin/bash
#This script requrest setuptools and mkdocs
./build-tools/newversion.sh ./setup.py
./build-tools/newversion.sh ./taskcat/taskcat.py
./build-tools/newversion.sh ./README.md
./build-tools/newversion.sh  docker/build_files/ubuntu/Dockerfile 
./build-tools/newversion.sh  docker/build_files/centos/Dockerfile 
VERSION=$(grep version taskcat/taskcat.py |head -1 | awk -F'=|,' '{print $2}' | sed -e s/\'//|tr -d " "|tr -d "'")
echo $VERSION
python setup.py sdist 
python setup.py bdist_wheel 
python -m mkdocs gh-deploy --clean  
#python setup.py upload_docs --upload-dir=site

git tag $VERSION
git push --tags origin master
git commit -m "release $VERSION"

twine upload dist/*

rm -rf  dist/*
rm  -rf build/*
