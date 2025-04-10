FROM python:3.13-alpine

# Install dependencies
RUN pip3 install --no-cache-dir --upgrade aistore[etl]>=1.13.2

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY md5_server.py md5_server.py

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000
