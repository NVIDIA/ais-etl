FROM docker.io/library/python:3.13-alpine

RUN pip3 install --upgrade aistore[etl]>=1.13.5

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY flask_server.py fastapi_server.py http_server.py ./

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000
