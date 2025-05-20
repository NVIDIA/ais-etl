ARG PYTHON_VERSION

FROM docker.io/library/python:${PYTHON_VERSION}-alpine

# TODO: Change after aistore 1.13.7 is released
# Install git and build dependencies
RUN apk update && apk add --no-cache git
# RUN pip3 install --upgrade aistore[etl]>=1.13.7
RUN pip install --no-cache-dir --upgrade \
    "git+https://github.com/NVIDIA/aistore.git@webserver-utils#subdirectory=python" \
    "fastapi>=0.109.1" \
    "httpx>=0.28.0" \
    "aiofiles>=23.2.1" \
    "uvicorn[standard]>=0.32.0" \
    "flask>=2.3.0" \
    "gunicorn>=23.0.0"

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY bootstrap.py server.py ./

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000
