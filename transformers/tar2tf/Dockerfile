FROM golang:1.21-alpine

RUN apk add --no-cache git

RUN mkdir $GOPATH/tar2tf
WORKDIR $GOPATH/tar2tf
COPY src/ ./
RUN go build -o tar2tf

EXPOSE 80
