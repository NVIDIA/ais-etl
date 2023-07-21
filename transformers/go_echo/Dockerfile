FROM golang:1.16-alpine3.12

RUN apk add --no-cache git

RUN mkdir $GOPATH/echo
WORKDIR $GOPATH/echo
COPY src/ ./
RUN go build -o echo

EXPOSE 80
