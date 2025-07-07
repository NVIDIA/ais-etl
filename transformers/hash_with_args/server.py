#!/usr/bin/env python

"""
HTTP ETL Server for computing xxHash with configurable seed.

This server processes PUT and GET requests, computing xxHash of the content
with a configurable seed value passed via etl_args parameter.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import argparse
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

import requests
import xxhash

host_target = os.environ["AIS_TARGET_URL"]
seed_default = int(os.getenv("SEED_DEFAULT", "0"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class Handler(BaseHTTPRequestHandler):  # pylint: disable=missing-class-docstring
    def log_request(self, code="-", size="-"):
        # Don't log successful requests info. Unsuccessful logged by log_error().
        pass

    def _set_headers(self):
        """Set HTTP response headers."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def do_PUT(self):  # pylint: disable=invalid-name,missing-function-docstring
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            parsed_url = urlparse(self.path)
            seed = seed_default
            logging.info("PUT request received")
            params = parse_qs(parsed_url.query)
            if "etl_args" in params:
                seed = int(params["etl_args"][0])
                logging.info("PUT request with seed %d", seed)

            hash_result = self.calculate_xxhash(post_data, seed)
            self._set_headers()
            self.wfile.write(hash_result.encode())
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Error in PUT request: %s", e)
            self.send_error(500, f"Internal Server Error: {e}")

    def do_GET(self):  # pylint: disable=invalid-name,missing-function-docstring
        if self.path == "/health":
            self._set_headers()
            self.wfile.write(b"Running")
            return

        try:
            parsed_url = urlparse(self.path)
            x = requests.get(host_target + self.path, timeout=10)

            seed = seed_default
            logging.info("GET request received")
            params = parse_qs(parsed_url.query)
            if "etl_args" in params:
                seed = int(params["etl_args"][0])
                logging.info("GET request with seed %d", seed)

            hash_result = self.calculate_xxhash(x.content, seed)
            self._set_headers()
            self.wfile.write(hash_result.encode())
        except requests.HTTPError as http_err:
            logging.error("HTTP error in GET request: %s", http_err)
            self.send_error(502, f"Bad Gateway: {http_err}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Error in GET request: %s", e)
            self.send_error(500, f"Internal Server Error: {e}")

    def calculate_xxhash(
        self, data, seed
    ):  # pylint: disable=missing-function-docstring
        hasher = xxhash.xxh64(seed=seed)
        hasher.update(data)
        return hasher.hexdigest()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(addr="localhost", port=8000):
    """Start the threaded HTTP server."""
    logging.info("Starting HTTP server on %s:%s", addr, port)
    try:
        server = ThreadedHTTPServer((addr, port), Handler)
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down the server.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Unexpected server error: %s", e)
    finally:
        logging.info("Server stopped.")


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
