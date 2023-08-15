FROM python:3.11-alpine

WORKDIR /

COPY ./requirements.txt requirements.txt

RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

COPY main.py main.py

ENV PYTHONUNBUFFERED 1

EXPOSE 8000
