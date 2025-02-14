FROM python:3.11-alpine

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

RUN mkdir /code
WORKDIR /code
COPY server.py server.py

ENV PYTHONUNBUFFERED 1

EXPOSE 80

ENTRYPOINT [ "/code/server.py", "--listen", "0.0.0.0", "--port", "80" ]
