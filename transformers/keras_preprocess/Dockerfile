FROM docker.io/library/python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fastapi_server.py ./

EXPOSE 8000

# Run FastAPI app with uvicorn
ENTRYPOINT ["uvicorn", "fastapi_server:fastapi_app", "--host", "0.0.0.0", "--workers", "6", "--log-level", "info", "--ws-max-size", "17179869184", "--ws-ping-interval", "0", "--ws-ping-timeout", "86400", "--no-access-log"]