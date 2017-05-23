FROM nginx:1.13

RUN apt-get update && apt-get -y install curl git gcc make

# Set up docker
ENV DOCKER_BUCKET get.docker.com
ENV DOCKER_VERSION 1.13.1
ENV DOCKER_SHA256 97892375e756fd29a304bd8cd9ffb256c2e7c8fd759e12a55a6336e15100ad75
RUN set -x \
	&& curl -fSL "https://${DOCKER_BUCKET}/builds/Linux/x86_64/docker-${DOCKER_VERSION}.tgz" -o docker.tgz \
	&& echo "${DOCKER_SHA256} *docker.tgz" | sha256sum -c - \
	&& tar -xzvf docker.tgz \
	&& mv docker/* /usr/local/bin/ \
	&& rmdir docker \
	&& rm docker.tgz \
	&& docker -v

RUN apt-get install -y libssl-dev zlib1g-dev

# Install python
RUN curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash
RUN export PATH="/root/.pyenv/bin:$PATH" && pyenv install 3.6.1 && \
	pyenv global 3.6.1
ENV PATH=/root/.pyenv/plugins/pyenv-virtualenv/shims:/root/.pyenv/shims:/root/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Add Python script
RUN pip install ipython colorlog
ADD service_configurator.py /home

WORKDIR /home

ADD entry_point.sh /home/entry_point.sh

CMD ["bash", "/home/entry_point.sh"]