"""
Constants for testing transformers.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os

# -----------------------------------------------------------------------------
# Volume‐mount blocks
# -----------------------------------------------------------------------------
MINIKUBE_VOLUME_MOUNTS = """
      volumeMounts:
        - name: ais
          mountPath: /tmp/
  volumes:
    - name: ais
      hostPath:
        path: /tmp/
        type: Directory
"""

PROD_VOLUME_MOUNTS = """
      volumeMounts:
        - name: sda
          mountPath: /ais/sda
        - name: sdb
          mountPath: /ais/sdb
        - name: sdc
          mountPath: /ais/sdc
        - name: sdd
          mountPath: /ais/sdd
        - name: sde
          mountPath: /ais/sde
        - name: sdf
          mountPath: /ais/sdf
        - name: sdg
          mountPath: /ais/sdg
        - name: sdh
          mountPath: /ais/sdh
        - name: sdi
          mountPath: /ais/sdi
        - name: sdj
          mountPath: /ais/sdj
  volumes:
    - name: sda
      hostPath:
        path: /ais/sda
        type: Directory
    - name: sdb
      hostPath:
        path: /ais/sdb
        type: Directory
    - name: sdc
      hostPath:
        path: /ais/sdc
        type: Directory
    - name: sdd
      hostPath:
        path: /ais/sdd
        type: Directory
    - name: sde
      hostPath:
        path: /ais/sde
        type: Directory
    - name: sdf
      hostPath:
        path: /ais/sdf
        type: Directory
    - name: sdg
      hostPath:
        path: /ais/sdg
        type: Directory
    - name: sdh
      hostPath:
        path: /ais/sdh
        type: Directory
    - name: sdi
      hostPath:
        path: /ais/sdi
        type: Directory
    - name: sdj
      hostPath:
        path: /ais/sdj
        type: Directory
"""

# -----------------------------------------------------------------------------
# Pick the correct block based on DEPLOY_ENV (defaults to 'minikube')
# -----------------------------------------------------------------------------
DEPLOY_ENV = os.environ.get("DEPLOY_ENV", "minikube").lower()
if DEPLOY_ENV == "prod":
    VOLUME_MOUNTS = PROD_VOLUME_MOUNTS
else:
    VOLUME_MOUNTS = MINIKUBE_VOLUME_MOUNTS

# -----------------------------------------------------------------------------
# Shared command definitions
# -----------------------------------------------------------------------------
SERVER_COMMANDS = {
    "flask": [
        "gunicorn",
        "flask_server:flask_app",
        "--bind",
        "0.0.0.0:8000",
        "--workers",
        "6",
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
        "6",
    ],
    "http": ["python", "http_server.py"],
}

# -----------------------------------------------------------------------------
# Pod‐spec templates
# -----------------------------------------------------------------------------
ECHO_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-echo
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_echo:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {{command}}
      readinessProbe:
        httpGet:
          path: /health
          port: default
{VOLUME_MOUNTS}
"""

HELLO_WORLD_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-hello-world
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_hello_world:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {{command}}
      readinessProbe:
        httpGet:
          path: /health
          port: default
{VOLUME_MOUNTS}
"""

MD5_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-md5
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_md5:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {{command}}
      readinessProbe:
        httpGet:
          path: /health
          port: default
{VOLUME_MOUNTS}
"""
