FROM docker.io/library/python:3.13-alpine

RUN pip3 install --upgrade aistore[etl]>=1.13.6

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY flask_server.py fastapi_server.py http_server.py ./

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000

# Set default entrypoint to run the FastAPI server
# Runs with 6 workers, but can be overridden with 'command: ' in etl-spec.yaml
ENTRYPOINT ["uvicorn", "fastapi_server:fastapi_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "6", "--log-level", "info", "--ws-max-size", "17179869184", "--ws-ping-interval", "0", "--ws-ping-timeout", "86400", "--no-access-log"]