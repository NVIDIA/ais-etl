FROM python:3.8.5-alpine3.12

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

RUN mkdir /code
WORKDIR /code
COPY server.py server.py

ENV PYTHONUNBUFFERED 1

EXPOSE 80

ENTRYPOINT [ "/code/server.py", "--listen", "0.0.0.0", "--port", "80" ]
