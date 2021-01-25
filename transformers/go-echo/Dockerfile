FROM golang:1.15

RUN apt-get install git

RUN mkdir $GOPATH/echo
WORKDIR $GOPATH/echo
COPY src/ ./
RUN go build -o echo

EXPOSE 80