"""A simple echo server that returns the input data as output.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

"""

from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class EchoServer(FastAPIServer):
    """
    A simple echo server that returns the input data as output.
    """

    def transform(self, data, _path):
        return data


if __name__ == "__main__":
    server = EchoServer(port=8000)
    server.start()
