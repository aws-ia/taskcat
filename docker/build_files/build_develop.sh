cd centos-develop
VERSION="0.1.58"
IMAGE="taskcat-develop"
ORG="taskcat"

docker build -t taskcat:${VERSION} . 
ID="$(docker images | grep $VERSION | grep taskcat | head -n 1 | awk '{print $3}')"
docker tag $ID $ORG/$IMAGE:$ID
docker tag $ID $ORG/$IMAGE:latest
docker push $ORG/$IMAGE 
cd ..
