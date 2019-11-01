#!/bin/sh
set -e

cd /taskcat

/usr/local/bin/dockerd \
	--host=unix:///var/run/docker.sock \
	--host=tcp://127.0.0.1:2375 \
	--storage-driver=overlay2 &>/var/log/docker.log &


tries=0
d_timeout=60
until docker info >/dev/null 2>&1
do
	if [ "$tries" -gt "$d_timeout" ]; then
                cat /var/log/docker.log
		echo 'Timed out trying to connect to internal docker host.' >&2
		exit 1
	fi
        tries=$(( $tries + 1 ))
	sleep 1
done

eval "$(pyenv init -)"

for ver in "3.7.4" "3.6.9" ; do
    pyenv shell ${ver}
    pip install --upgrade pip > /dev/null 2> /dev/null
    pip install -r ./dev-requirements.txt > /dev/null
    pip install -e . > /dev/null
done

run-e2e.sh 3.7.4 3.6.9
