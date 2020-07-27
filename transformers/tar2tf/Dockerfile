FROM golang:1.13-alpine

RUN apk add git

RUN mkdir $GOPATH/tar2tf
WORKDIR $GOPATH/tar2tf
COPY src/ ./
RUN go get && go build -o tar2tf

EXPOSE 80
