"""
MD5 Hashing ETL Transformer (Fast-API)

This module implements an ETL transformer as a FastAPI-based server
that computes the MD5 checksum of each incoming request's payload
and returns the hexadecimal digest in the response body.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import hashlib
from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class Md5Server(FastAPIServer):
    """
    FastAPI-based HTTP server for MD5 hashing.

    Inherits from FastAPIServer to handle concurrent transform requests.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        super().__init__(host=host, port=port)
        self.md5_hash = hashlib.md5()

    def transform(self, data: bytes, *_args) -> bytes:
        """
        Compute the MD5 digest of the request payload.
        """
        return hashlib.md5(data).hexdigest().encode()


# Create the server instance and expose the FastAPI app
fastapi_server = Md5Server(port=8000)
fastapi_server.logger.setLevel("DEBUG")
fastapi_app = fastapi_server.app  # Expose the FastAPI app
