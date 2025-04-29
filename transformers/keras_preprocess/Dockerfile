FROM docker.io/library/python:3.9-slim

WORKDIR /

COPY ./requirements.txt requirements.txt

RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

COPY main.py main.py

ENV PYTHONUNBUFFERED 1
ENV TF_ENABLE_ONEDNN_OPTS 0

EXPOSE 8000
