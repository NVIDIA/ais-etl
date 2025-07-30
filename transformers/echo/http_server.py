"""A simple echo server that returns the input data as output.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

"""

from aistore.sdk.etl.webserver.http_multi_threaded_server import HTTPMultiThreadedServer


class EchoServer(HTTPMultiThreadedServer):
    """
    A simple echo server that returns the input data as output.
    """

    def transform(self, data, *_args):
        return data


if __name__ == "__main__":
    echo_server = EchoServer(port=8000)
    echo_server.start()
