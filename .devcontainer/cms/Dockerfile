# syntax=docker/dockerfile:1
FROM ubuntu:22.04

ENV TZ Etc/UTC
ENV LANG C.UTF-8

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    cgroup-lite \
    cppreference-doc-en-html \
    fp-compiler \
    git \
    haskell-platform \
    libcap-dev \
    libcups2-dev \
    libffi-dev \
    libpq-dev \
    libyaml-dev \
    mono-mcs \
    nano \
    openjdk-8-jdk-headless \
    php8.1-cli \
    postgresql-client \
    python2 \
    python3-pip \
    python3.11 \
    python3.11-dev \
    rustc \
    sudo \
    zip

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

RUN useradd -ms /bin/bash cms
RUN usermod -aG sudo cms

RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER cms

RUN git clone --recurse-submodules https://github.com/cms-dev/cms /home/cms/cms/ && \
    git -C /home/cms/cms/ checkout b77c87b4d60fbe7df60dc5e03d2be632a25992fe

WORKDIR /home/cms/cms

COPY requirements.txt requirements.txt

RUN sudo pip3 install -r requirements.txt
RUN sudo pip3 install -r dev-requirements.txt

RUN find cms \
    -name "*.py" \
    -exec grep -Eq "(from|import) tornado" "{}" \; \
    -exec sed -i '2s;^;import collections\ncollections.MutableMapping = collections.abc.MutableMapping\n;' {} \;

RUN sudo python3 setup.py install

RUN sudo python3 prerequisites.py --yes --cms=cms install

COPY cms.conf /home/cms/cms.conf
RUN sudo cp /home/cms/cms.conf /usr/local/etc/cms.conf

EXPOSE 8888
EXPOSE 8889

CMD ["cmsLogService"]
