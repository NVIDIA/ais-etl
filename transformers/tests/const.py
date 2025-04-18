"""
Constants for testing transformers.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

SERVER_COMMANDS = {
    "flask": [
        "gunicorn",
        "flask_server:flask_app",
        "--bind",
        "0.0.0.0:8000",
        "--workers",
        "24",
        "--log-level",
        "debug",
    ],
    "fastapi": [
        "uvicorn",
        "fastapi_server:fastapi_app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--workers",
        "24",
    ],
    "http": ["python", "http_server.py"],
}

ECHO_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-echo
  annotations:
    communication_type: "{communication_type}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_echo:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {command}
      readinessProbe:
        httpGet:
          path: /health
          port: default
      volumeMounts:
        - name: ais
          mountPath: /tmp/
  volumes:
    - name: ais
      hostPath:
        path: /tmp/
        type: Directory
"""
