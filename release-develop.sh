#!/bin/bash
#This script build a new version of taskcat
./build-tools/new-develop-version.sh  setup-develop.py

python setup-develop.py sdist 
twine upload dist/*  -r test

rm -rf  dist/*
rm  -rf build/*

cd  docker/build_files/
./build_develop.sh
