#!/bin/bash -e

echo "Building codebuild image..."
cd e2e/codebuild/
docker build . -t taskcat-e2e:latest > /dev/null
docker build . -f Dockerfile-local -t taskcat-e2e-local:latest > /dev/null
cd ../../

echo "executing build... (privileged mode needed for docker in docker)"
docker run -it --privileged --rm --name taskcat-e2e \
  --mount type=bind,source="$(pwd)",target=/taskcat-v9 taskcat-e2e-local:latest
