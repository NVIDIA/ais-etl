#!/usr/bin/env python

#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import argparse
import bz2
import gzip
import json
import logging
import os

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import requests

host_target = os.environ["AIS_TARGET_URL"]
compress_options = json.loads(os.environ["COMPRESS_OPTIONS"])

if "mode" not in compress_options:
    mode = "compress"
else:
    mode = compress_options["mode"]

if "compression" not in compress_options:
    compression = "gzip"
else:
    compression = compress_options["compression"]


class Handler(BaseHTTPRequestHandler):
    # Overriding log_request to not log successful requests
    def log_request(self, code="-", size="-"):
        pass

    # Set standard headers for responses
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()

    def process_data(self, data):
        if mode == "compress" and compression == "gzip":
            return gzip.compress(data)
        if mode == "compress" and compression == "bz2":
            return bz2.compress(data)
        if mode == "decompress" and compression == "gzip":
            return gzip.decompress(data)
        if mode == "decompress" and compression == "bz2":
            return bz2.decompress(data)
        raise ValueError(
            f"Unsupported data processing mode ({mode}) or compression algorithm ({compression})"
        )

    # PUT handler supports `hpush` operation
    def do_PUT(self):
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            processed_data = self.process_data(post_data)
            self._set_headers()
            self.wfile.write(processed_data)
        except Exception as exception:
            logging.error("Error processing PUT request: %s", str(exception))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Data processing failed")

    # GET handler supports `hpull` operation
    def do_GET(self):
        try:
            if self.path == "/health":
                self._set_headers()
                self.wfile.write(b"OK")
                return

            response = requests.get(host_target + self.path)
            processed_data = self.process_data(response.content)

            self._set_headers()
            self.wfile.write(processed_data)

        except Exception as exception:
            logging.error("Error processing GET request: %s", str(exception))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Data processing failed")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(addr, port):
    server = ThreadedHTTPServer((addr, port), Handler)
    print(f"Starting HTTP server on {addr}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-l",
        "--listen",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Specify the port on which the server listens",
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port)
