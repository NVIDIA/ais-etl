FROM docker.io/library/python:slim

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade -r requirements.txt

RUN mkdir /code
WORKDIR /code
COPY server.py server.py

ENV PYTHONUNBUFFERED 1

EXPOSE 80
