FROM python:3.8.5-alpine3.12

RUN apk update
RUN apk add --no-cache ffmpeg

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

RUN mkdir /code
WORKDIR /code
COPY server.py server.py

ENV PYTHONUNBUFFERED 1

EXPOSE 80