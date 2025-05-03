"""A simple echo server that returns the input data as output.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

"""

from aistore.sdk.etl.webserver.flask_server import FlaskServer


class EchoServerFlask(FlaskServer):
    """
    A simple echo server that returns the input data as output.
    """

    def transform(self, data, *_args):
        return data


flask_server = EchoServerFlask(port=8000)
flask_server.logger.setLevel("DEBUG")
flask_app = flask_server.app
