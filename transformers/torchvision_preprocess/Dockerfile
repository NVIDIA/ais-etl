FROM python:3.11-slim

# Set working directory
WORKDIR /code

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY fastapi_server.py ./

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose default port
EXPOSE 8000

# Set default entrypoint to run the FastAPI server
# Runs with 4 workers, but can be overridden with 'command: ' in etl-spec.yaml
ENTRYPOINT ["uvicorn", "fastapi_server:fastapi_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info", "--ws-max-size", "17179869184", "--ws-ping-interval", "0", "--ws-ping-timeout", "86400", "--no-access-log"]
