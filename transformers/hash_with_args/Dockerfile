FROM python:3.13-alpine

# Install git and build dependencies
RUN apk update && apk add --no-cache git gcc musl-dev libffi-dev

# Set working directory
WORKDIR /code

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade \
    "git+https://github.com/NVIDIA/aistore.git@etl-args-webserver#subdirectory=python" \
    "fastapi>=0.109.1" \
    "httpx>=0.28.0" \
    "aiofiles>=23.2.1" \
    "uvicorn[standard]>=0.32.0" \
    "flask>=2.3.0" \
    "gunicorn>=23.0.0"

# Copy application code
COPY flask_server.py fastapi_server.py http_server.py ./

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose default port
EXPOSE 8000
