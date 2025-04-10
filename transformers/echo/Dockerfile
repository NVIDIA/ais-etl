FROM python:3.13-alpine

# Install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY echo_server.py echo_server.py

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000
