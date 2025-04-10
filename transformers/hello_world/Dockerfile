FROM python:3.13-alpine

# Install dependencies
RUN pip3 install aistore[etl]>=1.13.1

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY hello_world_server.py hello_world_server.py

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000
