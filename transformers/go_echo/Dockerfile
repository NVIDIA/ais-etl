FROM golang:1.21-alpine

RUN apk add --no-cache git

RUN mkdir $GOPATH/echo
WORKDIR $GOPATH/echo
COPY src/ ./
RUN go build -o echo

EXPOSE 80
