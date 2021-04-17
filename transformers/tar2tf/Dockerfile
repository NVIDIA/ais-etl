FROM golang:1.16-alpine3.12

RUN apk add --no-cache git

RUN mkdir $GOPATH/tar2tf
WORKDIR $GOPATH/tar2tf
COPY src/ ./
RUN go build -o tar2tf

EXPOSE 80
