#!/bin/bash
#This script requrest setuptools and mkdocs
./build-tools/newversion.sh ./setup.py
./build-tools/newversion.sh ./taskcat/taskcat.py
VERSION=$(grep version taskcat/taskcat.py |head -1 | awk -F'=|,' '{print $2}' | sed -e s/\'//|tr -d " "|tr -d "'")
echo $VERSION
rm  dist/*
python setup.py sdist 
python setup.py bdist_wheel 
python -m mkdocs gh-deploy --clean  
python setup.py upload_docs --upload-dir=site

git tag $VERSION
git push --tags origin master
git commit -m "release $VERSION"

twine upload dist/*
