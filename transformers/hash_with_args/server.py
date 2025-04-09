#!/usr/bin/env python

import argparse
import xxhash
import requests
import os
import logging
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

host_target = os.environ["AIS_TARGET_URL"]
seed_default = int(os.getenv("SEED_DEFAULT", "0"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        # Don't log successful requests info. Unsuccessful logged by log_error().
        pass

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def do_PUT(self):
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
        except Exception as e:
            logging.error("Error in PUT request: %s", e)
            self.send_error(500, f"Internal Server Error: {e}")

    def do_GET(self):
        if self.path == "/health":
            self._set_headers()
            self.wfile.write(b"Running")
            return

        try:
            parsed_url = urlparse(self.path)
            x = requests.get(host_target + self.path)

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
        except Exception as e:
            logging.error("Error in GET request: %s", e)
            self.send_error(500, f"Internal Server Error: {e}")

    def calculate_xxhash(self, data, seed):
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
    except Exception as e:
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
