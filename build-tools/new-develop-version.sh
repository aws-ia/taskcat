#!/bin/bash
if [[ $1 == "" ]];then
	echo "usage $0 filename"
	exit 1
fi

PLATFORM=`uname`

DEVELOP_VERSION=$(grep version setup-develop.py |head -1 | awk -F'=|,' '{print $2}' | sed -e s/\'//|tr -d " "|tr -d "'" |  awk '{print substr($0,length,1)}')
NEW_VERSION=$(echo -n $DEVELOP_VERSION| awk -F. '{$NF= $NF + 1;} 1' | sed 's/ /./g')
echo "Updating Version of [$(basename $1)] from [${CURRENT_VERSION}] to [${NEW_VERSION}]"

if [[ ${PLATFORM} == 'Darwin' ]]; then
sed -i '' -e "s/dev${DEVELOP_VERSION}/dev${NEW_VERSION}/" setup-develop.py
fi
