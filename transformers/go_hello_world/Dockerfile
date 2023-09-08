FROM golang:1.21-alpine3.18

RUN apk add --no-cache git

RUN mkdir $GOPATH/hello_world
WORKDIR $GOPATH/hello_world
COPY src/ ./
RUN go build -o hello_world

EXPOSE 80
