ARG PYTHON_VERSION

FROM golang:1.18 AS builder

ENV GOPATH="/go"
ENV PATH="${GOPATH}/bin:${PATH}"

WORKDIR /code

COPY ./io-comm/ /code

RUN make build

FROM python:${PYTHON_VERSION}

WORKDIR /

RUN pip --disable-pip-version-check install requests
COPY server.py /server.py

COPY --from=builder /code/server /server

EXPOSE 80

ENV PYTHONUNBUFFERED 1

CMD [ "python", "/server.py" ]
