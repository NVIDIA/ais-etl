"""
A HTTP-based beginner-friendly "Hello World" web server.

Responds with "Hello World!" to any GET or PUT request.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

"""

from aistore.sdk.etl.webserver.http_multi_threaded_server import HTTPMultiThreadedServer


class HelloWorldHTTPServer(HTTPMultiThreadedServer):
    """
    A simple HTTP-based ETL transformer that returns b"Hello World!" as output
    for any incoming data, regardless of the request path or content.
    """

    def transform(self, data, path):
        return b"Hello World!"


if __name__ == "__main__":
    http_server = HelloWorldHTTPServer(port=8000)
    http_server.logger.setLevel("DEBUG")
    http_server.start()
