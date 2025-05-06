FROM docker.io/library/python:3.13-alpine

# need this for soundfile
RUN apk add --no-cache libsndfile-dev
# Install dependencies
RUN pip3 install --upgrade aistore[etl]>=1.13.5 soundfile

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY fastapi_server.py ./

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000
