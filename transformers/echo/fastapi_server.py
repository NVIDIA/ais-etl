"""
A FastAPI echo server that returns the input data as output.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class EchoServerFastAPI(FastAPIServer):
    """
    A simple echo server using FastAPI that returns the input data as output.
    """

    def transform(self, data, *_args):
        return data


# Create the server instance and expose the FastAPI app
fastapi_server = EchoServerFastAPI(port=8000)
fastapi_app = fastapi_server.app  # Expose the FastAPI app
