#!/usr/bin/env python

import argparse
import hashlib
import requests
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

host_target = os.environ["AIS_TARGET_URL"]


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        pass  # Disable request logging

    def _set_headers(self, content_length):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(content_length))
        self.end_headers()

    def do_PUT(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        digest = hashlib.md5(post_data).hexdigest().encode()
        self._set_headers(len(digest))
        self.wfile.write(digest)

    def do_GET(self):
        if self.path == "/health":
            response = b"Running"
            self._set_headers(len(response))
            self.wfile.write(response)
            return

        content = requests.get(host_target + self.path).content
        digest = hashlib.md5(content).hexdigest().encode()
        self._set_headers(len(digest))
        self.wfile.write(digest)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""


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
