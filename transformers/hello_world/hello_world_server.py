"""A simple "Hello World!" ETL Transformation server.
It responds with "Hello World!" to any incoming request.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

"""

from aistore.sdk.etl.webserver import FastAPIServer


class HelloWorldServer(FastAPIServer):
    """
    A simple echo server that returns the input data as output.
    """

    def transform(self, data, path):
        return b"Hello World!"


if __name__ == "__main__":
    server = HelloWorldServer(port=8000)
    server.start()
