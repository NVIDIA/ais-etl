#!/usr/bin/env python

import argparse
import hashlib
import requests
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

host_target = os.environ['AIS_TARGET_URL']


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        # Don't log successful requests info. Unsuccessful logged by log_error().
        pass

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def do_PUT(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        md5 = hashlib.md5()
        md5.update(post_data)
        self._set_headers()
        self.wfile.write(md5.hexdigest().encode())

    def do_GET(self):
        if self.path == "/health":
            self._set_headers()
            self.wfile.write(b"Running")
            return

        x = requests.get(host_target + self.path)
        md5 = hashlib.md5()
        md5.update(x.content)
        self._set_headers()
        self.wfile.write(md5.hexdigest().encode())


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(addr="localhost", port=8000):
    server = ThreadedHTTPServer((addr, port), Handler)
    print(f"Starting HTTP server on {addr}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-l",
        "--listen",
        default="localhost",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Specify the port on which the server listens",
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port)
