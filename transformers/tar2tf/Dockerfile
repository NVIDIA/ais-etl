FROM golang:1.13-alpine

RUN apk add git

RUN mkdir $GOPATH/tar2tf
WORKDIR $GOPATH/tar2tf
COPY main.go io.go utils.go go.mod go.sum cached.go ./
RUN go get && go build -o tar2tf

EXPOSE 80

ENTRYPOINT [ "./tar2tf", "-l", "0.0.0.0", "-p", "80" ]
