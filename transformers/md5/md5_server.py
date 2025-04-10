"""
MD5 Hashing Server
This ETL transformer implements a multi-threaded HTTP server that computes the MD5 hash
of incoming request data.
"""

import logging
import hashlib
from aistore.sdk.etl.webserver import HTTPMultiThreadedServer


class Md5Server(HTTPMultiThreadedServer):
    """
    Multi-threaded HTTP server that computes the MD5 hash of the request data.
    """

    def __init__(self):
        super().__init__(host="0.0.0.0", port=8000)
        self.logger.setLevel(logging.DEBUG)
        self.md5_hash = hashlib.md5()

    def transform(self, data, path):
        self.logger.debug("Transforming request data for path: %s", path)
        digest = hashlib.md5(data).hexdigest()
        return digest.encode()


if __name__ == "__main__":
    server = Md5Server()
    server.start()
