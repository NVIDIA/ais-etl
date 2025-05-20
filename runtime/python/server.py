"""
Entry point for launching a deserialized ETL server instance.
This module reads a base64-encoded ETL class definition from the
ETL_CLASS_PAYLOAD environment variable, deserializes it into a subclass
of `ETLServer`, and instantiates it.

This file is intended to be used by uvicorn/gunicorn like:
    uvicorn server:server.app --workers=4 ...

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
from typing import Type
import logging

from aistore.sdk.etl.webserver.base_etl_server import ETLServer
from aistore.sdk.etl.webserver.utils import deserialize_class

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
try:
    ETLClass: Type[ETLServer] = deserialize_class(ETL_CLASS_PAYLOAD)
except Exception as e:
    raise RuntimeError(f"Failed to deserialize ETL class: {e}") from e
server = ETLClass()
