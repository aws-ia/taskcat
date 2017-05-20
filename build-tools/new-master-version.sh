#!/bin/bash
if [[ $1 == "" ]];then
	echo "usage $0 filename"
	exit 1
fi

PLATFORM=`uname`

CURRENT_VERSION=$(grep version $1|head -1 | awk -F'=|,' '{print $2}' | sed -e s/\'//|tr -d " "|tr -d "'")
NEW_VERSION=$(echo -n $CURRENT_VERSION | awk -F. '{$NF= $NF + 1;} 1' | sed 's/ /./g')
echo "Updating Version of [$(basename $1)] from [${CURRENT_VERSION}] to [${NEW_VERSION}]"

if [[ ${PLATFORM} == 'Darwin' ]]; then
sed -i '' -e "s/${CURRENT_VERSION}/${NEW_VERSION}/" $1
fi

