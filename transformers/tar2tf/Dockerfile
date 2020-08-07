FROM golang:1.13-buster

RUN apt-get install git

RUN mkdir $GOPATH/tar2tf
WORKDIR $GOPATH/tar2tf
COPY src/ ./
RUN go get && go build -o tar2tf

EXPOSE 80
