"""
MD5 Hashing ETL Transformer (Flask)

This module implements an ETL transformer as a Flask-based HTTP server
that computes the MD5 checksum of each incoming request's payload
and returns the hexadecimal digest in the response body.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import hashlib
from aistore.sdk.etl.webserver.flask_server import FlaskServer


class Md5Server(FlaskServer):
    """
    Flask-based HTTP server for MD5 hashing.

    Inherits from FlaskServer to handle concurrent transform requests.
    """

    def transform(self, data: bytes, *_args) -> bytes:
        """
        Compute the MD5 digest of the request payload.
        """
        return hashlib.md5(data).hexdigest().encode()


flask_server = Md5Server(port=8000)
flask_app = flask_server.app
