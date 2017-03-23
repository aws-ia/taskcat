cd $1
docker build -t taskcat .
docker tag taskcat:latest taskcat/taskcat:latest
docker push taskcat/taskcat 
cd ..
