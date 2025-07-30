"""
A FastAPI-based beginner-friendly "Hello World" web server.

Responds with "Hello World!" to any GET or PUT request.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class HelloWorldServerFastAPI(FastAPIServer):
    """
    A simple FastAPI-based ETL transformer that returns b"Hello World!" as output
    for any incoming data, regardless of the request path or content.
    """

    def transform(self, *_args) -> bytes:
        return b"Hello World!"


# Instantiate the server and expose its FastAPI app
fastapi_server = HelloWorldServerFastAPI(port=8000)
fastapi_app = fastapi_server.app  # This is what uvicorn will run
