"""
Constants for testing transformers.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
from itertools import product

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_WS

# -----------------------------------------------------------------------------
# Volume‐mount blocks
# -----------------------------------------------------------------------------
MINIKUBE_VOLUME_MOUNTS = """
      volumeMounts:
        - name: ais
          mountPath: /mnt/data
  volumes:
    - name: ais
      hostPath:
        path: /mnt/data
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
# Environment
# Pick the correct block based on DEPLOY_ENV (defaults to 'minikube')
# -----------------------------------------------------------------------------
DEPLOY_ENV = os.getenv("DEPLOY_ENV", "minikube").lower()
if DEPLOY_ENV == "prod":
    VOLUME_MOUNTS = PROD_VOLUME_MOUNTS
    NUM_WORKERS = 24
else:
    VOLUME_MOUNTS = MINIKUBE_VOLUME_MOUNTS
    NUM_WORKERS = 4

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
        str(NUM_WORKERS),
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
        str(NUM_WORKERS),
        "--log-level",
        "info",
        # WebSocket tuning:
        "--ws-max-size",
        "17179869184",  # ~16 GiB
        "--ws-ping-interval",
        "0",  # disable automatic pings
        "--ws-ping-timeout",
        "86400",  # 24 h before timing out a missing pong
        "--no-access-log",
    ],
    "http": [
        "python",
        "http_server.py",
    ],
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
    support_direct_put: "{{direct_put}}"
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

ECHO_GO_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: echo-go
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_echo_go:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: ['./echo', '-l', '0.0.0.0', '-p', '8000']
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
    support_direct_put: "{{direct_put}}"
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
    support_direct_put: "{{direct_put}}"
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

FFMPEG_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-nemo-ffmpeg
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_ffmpeg:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {{command}}
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: AR
          value: "16000"
        - name: AC
          value: "1"
{VOLUME_MOUNTS}
"""

FFMPEG_GO_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-nemo-ffmpeg-go
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_ffmpeg_go:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: ['./go_ffmpeg', '-l', '0.0.0.0', '-p', '8000']
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: AR
          value: "16000"
        - name: AC
          value: "1"
{VOLUME_MOUNTS}
"""

HASH_WITH_ARGS_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-hash-with-args
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_hash_with_args:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {{command}}
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: SEED_DEFAULT
          value: "0"
{VOLUME_MOUNTS}
"""

AUDIO_SPLITTER_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-audio-splitter
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_audio_splitter:latest
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

AUDIO_MANAGER_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-audio-manager
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_audio_manager:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {{command}}
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: AIS_ENDPOINT
          value: "{{ais_endpoint}}"
        - name: SRC_BUCKET
          value: "{{bck_name}}"
        - name: SRC_PROVIDER
          value: "ais"  
        - name: OBJ_PREFIX
          value: ""
        - name: OBJ_EXTENSION
          value: "wav"
        - name: ETL_NAME
          value: "{{etl_name}}"
{VOLUME_MOUNTS}
"""

FACE_DETECTION_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-face-detection
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_face_detection:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {{command}}
      env:
        - name: FORMAT
          value: "{{format}}"
        - name: ARG_TYPE
          value: "{{arg_type}}"
      readinessProbe:
        httpGet:
          path: /health
          port: default
{VOLUME_MOUNTS}
"""

# TODO: Fix template
KERAS_TRANSFORMER = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-keras
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_keras:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: ["gunicorn", "main:app", "--workers", "20", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"] 
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: FORMAT
          value: "{{format}}"
        - name: TRANSFORM
          value: '{{transform}}'
        - name: ARG_TYPE
          value: "{{arg_type}}"
{VOLUME_MOUNTS}
"""

BATCH_RENAME_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-batch-rename
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_batch_rename:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: ["uvicorn", "fastapi_server:fastapi_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--no-access-log"]
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: AIS_ENDPOINT
          value: "{{ais_endpoint}}"
        - name: DST_BUCKET
          value: "{{bck_name}}"
        - name: DST_BUCKET_PROVIDER
          value: "ais"
        - name: FILE_PATTERN
          value: '{{regex_pattern}}'
        - name: DST_PREFIX
          value: "{{dst_prefix}}"
{VOLUME_MOUNTS}
"""

COMPRESS_TEMPLATE = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-compress
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 5m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_compress:latest
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

TORCHVISION_TRANSFORMER = f"""
apiVersion: v1
kind: Pod
metadata:
  name: transformer-torchvision
  annotations:
    communication_type: "{{communication_type}}://"
    wait_timeout: 10m
    support_direct_put: "{{direct_put}}"
spec:
  containers:
    - name: server
      image: aistorage/transformer_torchvision:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: {{command}}
      env:
        - name: FORMAT
          value: "{{format}}"
        - name: TRANSFORM
          value: '{{transform}}'
      readinessProbe:
        httpGet:
          path: /health
          port: default
{VOLUME_MOUNTS}
"""

# -----------------------------------------------------------------------------
# Parameter grids
# -----------------------------------------------------------------------------
SERVER_TYPES = ["flask", "fastapi", "http"]
COMM_TYPES = [ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_WS]
FQN_OPTIONS = [True, False]
DIRECT_PUT_OPTIONS = ["true", "false"]
PARAM_COMBINATIONS = [
    (srv, comm, fqn, direct_put)
    for srv, comm, fqn, direct_put in product(
        SERVER_TYPES, COMM_TYPES, FQN_OPTIONS, DIRECT_PUT_OPTIONS
    )
    # Cannot run ws communication with flask or http servers
    # Cannot run ws communication without direct put
    if not (
        (comm == "ws" and (srv in ["http", "flask"]))
        or (comm == "ws" and direct_put == "false")
    )
]

GO_PARAM_COMBINATIONS = [
    (comm, fqn, direct_put)
    for comm, fqn, direct_put in product(COMM_TYPES, FQN_OPTIONS, DIRECT_PUT_OPTIONS)
    # Cannot run ws communication without direct put
    if not (comm == "ws" and direct_put == "false")
]

INLINE_PARAM_COMBINATIONS = [
    (srv, comm, fqn)
    for srv, comm, fqn in product(SERVER_TYPES, COMM_TYPES, FQN_OPTIONS)
    # Cannot run ws communication for inline transformations
    # Direct put only works on offline tranformations
    if not (comm == "ws")
]

# -----------------------------------------------------------------------------
# Test parameter combinations
# -----------------------------------------------------------------------------
FASTAPI_PARAM_COMBINATIONS = list(
    product(
        ["fastapi"],  # server_type
        [ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_WS],  # comm_type
        [True, False],  # use_fqn
    )
)

# -----------------------------------------------------------------------------
# Label Format
# -----------------------------------------------------------------------------

LABEL_FMT = "{name:<12} | {server:<9} | {comm:<6} | {arg:<4} | {direct:<12} | "
