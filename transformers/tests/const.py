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
