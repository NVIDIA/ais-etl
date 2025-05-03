"""
MD5 Hashing ETL Transformer

This module implements an ETL transformer as a multi-threaded HTTP server
that computes the MD5 checksum of each incoming request's payload
and returns the hexadecimal digest in the response body.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import hashlib
from aistore.sdk.etl.webserver import HTTPMultiThreadedServer


class Md5Server(HTTPMultiThreadedServer):
    """
    Multi-threaded HTTP server for MD5 hashing.

    Inherits from HTTPMultiThreadedServer to handle concurrent transform
    requests. Each request body is hashed independently.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        super().__init__(host=host, port=port)
        self.md5_hash = hashlib.md5()

    def transform(self, data: bytes, *_args) -> bytes:
        """
        Compute the MD5 digest of the request payload.
        """
        digest = hashlib.md5(data).hexdigest()
        return digest.encode()


if __name__ == "__main__":
    server = Md5Server()
    server.logger.setLevel("DEBUG")
    server.start()
