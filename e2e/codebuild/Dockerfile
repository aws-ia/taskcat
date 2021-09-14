FROM amazonlinux:2
MAINTAINER taskcat-dev-team

ENV PATH="/root/.pyenv/bin:$PATH"\
 DOCKER_VERSION="18.09.6" \
 DOCKER_COMPOSE_VERSION="1.24.0"

#****************        Utilities     *********************************************
ENV DOCKER_BUCKET="download.docker.com" \
    DOCKER_CHANNEL="stable" \
    DOCKER_SHA256="1f3f6774117765279fce64ee7f76abbb5f260264548cf80631d68fb2d795bb09" \
    DIND_COMMIT="3b5fac462d21ca164b3778647420016315289034"

RUN yum install -y wget tar git make gcc openssl-devel bzip2-devel sqlite-devel \
    libffi-devel readline-devel libxml2-dev libxslt-dev e2fsprogs iptables xfsprogs \
    fakeroot && \
    yum clean all

RUN set -ex \
    && curl -fSL "https://${DOCKER_BUCKET}/linux/static/${DOCKER_CHANNEL}/x86_64/docker-${DOCKER_VERSION}.tgz" -o docker.tgz \
    && echo "${DOCKER_SHA256} *docker.tgz" | sha256sum -c - \
    && tar --extract --file docker.tgz --strip-components 1  --directory /usr/local/bin/ \
    && rm docker.tgz \
    && docker -v \
    && groupadd dockremap \
    && useradd -g dockremap dockremap \
    && echo 'dockremap:165536:65536' >> /etc/subuid \
    && echo 'dockremap:165536:65536' >> /etc/subgid \
    && wget "https://raw.githubusercontent.com/docker/docker/${DIND_COMMIT}/hack/dind" -O /usr/local/bin/dind \
    && curl -L https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-Linux-x86_64 > /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/dind /usr/local/bin/docker-compose \
    && docker-compose version

RUN curl -L \
        https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | \
        bash && \
    eval "$(pyenv init -)" && \
    export PATH="$HOME/.pyenv/bin:$PATH" && \
    pyenv install 3.7.4 && \
    pyenv global 3.7.4 && \
    $(pyenv which pip) --no-cache-dir install boto3 "PyGithub>=1.43.8"

COPY install.sh /usr/local/bin/
COPY run-e2e.sh /usr/local/bin/
COPY results_comment.py /
COPY dockerd-entrypoint.sh /usr/local/bin/

VOLUME /var/lib/docker

ENTRYPOINT ["dockerd-entrypoint.sh"]
