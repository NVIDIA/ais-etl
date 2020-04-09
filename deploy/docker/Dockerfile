FROM golang:1.13-buster

RUN apt-get clean && apt-get update &&\
  set -eux &&\
  apt-get --no-install-recommends -y install curl git ca-certificates wget vim python3-setuptools python3 python3-pip \
   python3-venv sysstat attr net-tools iproute2 build-essential lsof iputils-ping fuse &&\
  apt-get -y clean all

RUN pip3 install awscli

ARG cld_provider=0
ENV CLD_PROVIDER ${cld_provider}

COPY requirements-jupyter.txt .
RUN pip3 install virtualenv && virtualenv -p /usr/bin/python3 /venv && . /venv/bin/activate && \
    pip3 install -r requirements-jupyter.txt && rm requirements-jupyter.txt

RUN mkdir -p $GOPATH/src/github.com/NVIDIA/ && git clone https://github.com/NVIDIA/aistore.git $GOPATH/src/github.com/NVIDIA/aistore && echo "$GOPATH/src/github.com/NVIDIA/" && ls $GOPATH/src/github.com/NVIDIA/
COPY . $GOPATH/src/github.com/NVIDIA/ais-tar2tf/

WORKDIR $GOPATH/src/github.com/NVIDIA/ais-tar2tf/
EXPOSE 8888

ENTRYPOINT [ "sh", "-c", "$GOPATH/src/github.com/NVIDIA/ais-tar2tf/deploy/docker/entrypoint.sh" ]
