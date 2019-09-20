#!/bin/bash -ex

echo "Building codebuild image..."
cd e2e/codebuild/
docker build . -t taskcat-e2e:latest > /dev/null
docker build . -f Dockerfile-local -t taskcat-e2e-local:latest > /dev/null
cd ../../


echo "getting temporary credentials..."
ROLE_ARN=$(aws iam list-roles --region us-east-1 \
  --query 'Roles[?RoleName == `taskcat-e2e-test`].Arn' --output text)
if [[ $(echo "${ROLE_ARN}" | grep -c "taskcat-e2e-test") -eq 0 ]] ; then
  echo "creating AdministratorAccess role taskcat-e2e-test..."
  ARN=$(aws sts get-caller-identity --query 'Arn' --output text --region us-east-1)
  POLICY_DOC="{\"Version\": \"2012-10-17\", \"Statement\": [{\"Sid\": \"\", \"Effect\": \"Allow\", \"Principal\": {\"AWS\": \"${ARN}\"}, \"Action\": \"sts:AssumeRole\"}]}"
  ROLE_ARN=$(aws iam create-role --role-name "taskcat-e2e-test" \
    --description "taskcat e2e test role" \
    --assume-role-policy-document "${POLICY_DOC}" \
    --region us-east-1 --query 'Role.Arn')
  aws iam attach-role-policy --role-name "taskcat-e2e-test" \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess --region us-east-1
fi
read -r AKI SAK ST <<< $(aws sts assume-role --role-arn ${ROLE_ARN} \
  --role-session-name local-e2e-test \
  --query '[Credentials.AccessKeyId, Credentials.SecretAccessKey, Credentials.SessionToken]' \
  --output text)


echo "executing build... (privileged mode needed for docker in docker)"
docker run -it --privileged --rm --name taskcat-e2e \
  --mount type=bind,source="$(pwd)",target=/taskcat-v9 -e AWS_ACCESS_KEY_ID=${AKI} \
  -e AWS_SECRET_ACCESS_KEY=${SAK} -e AWS_SESSION_TOKEN=${ST} \
  taskcat-e2e-local:latest
