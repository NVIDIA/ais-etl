"""
Entry point for launching a deserialized ETL server instance.
This module reads a base64-encoded ETL class definition from the
ETL_CLASS_PAYLOAD environment variable, deserializes it into a subclass
of `ETLServer`, and instantiates it.

This file is intended to be used by uvicorn/gunicorn like:
    uvicorn server:server.app --workers=4 ...

This file serves as the application entry point for multi-worker uvicorn deployments.
When uvicorn is configured with multiple workers (num_workers > 1), it requires
a separate module to import and run in worker processes, necessitating this
dedicated server module.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import logging

from bootstrap import deserialize_class

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# ------------------------------------------------------------------------------
# Load and validate payload
# ------------------------------------------------------------------------------
ETL_CLASS_PAYLOAD: str = os.getenv("ETL_CLASS_PAYLOAD", "")
if not ETL_CLASS_PAYLOAD:
    raise RuntimeError("ETL_CLASS_PAYLOAD environment variable is not set")

# ------------------------------------------------------------------------------
# Deserialize the ETL class and instantiate the server
# ------------------------------------------------------------------------------
etl_class = deserialize_class(ETL_CLASS_PAYLOAD)
server = etl_class()
