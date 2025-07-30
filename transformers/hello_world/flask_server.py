"""
A Flask-based beginner-friendly "Hello World" web server.

Responds with "Hello World!" to any GET or PUT request.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

"""

from aistore.sdk.etl.webserver.flask_server import FlaskServer


class HelloWorldServerFlask(FlaskServer):
    """
    A simple Flask-based ETL transformer that returns b"Hello World!" as output
    for any incoming data, regardless of the request path or content.
    """

    def transform(self, *_args) -> bytes:
        return b"Hello World!"


flask_server = HelloWorldServerFlask(port=8000)
flask_app = flask_server.app
