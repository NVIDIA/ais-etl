"""
MD5 Hashing ETL Transformer

This module implements an ETL transformer as a multi-threaded HTTP server
that computes the MD5 checksum of each incoming request's payload
and returns the hexadecimal digest in the response body.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import hashlib
from aistore.sdk.etl.webserver.http_multi_threaded_server import HTTPMultiThreadedServer


class Md5Server(HTTPMultiThreadedServer):
    """
    Multi-threaded HTTP server for MD5 hashing.

    Inherits from HTTPMultiThreadedServer to handle concurrent transform
    requests. Each request body is hashed independently.
    """

    def transform(self, data: bytes, *_args) -> bytes:
        """
        Compute the MD5 digest of the request payload.
        """
        return hashlib.md5(data).hexdigest().encode()


if __name__ == "__main__":
    server = Md5Server()
    server.logger.setLevel("DEBUG")
    server.start()
