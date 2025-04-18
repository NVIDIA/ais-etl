#!/usr/bin/env python
import os
import importlib.util
from typing import Iterator
from inspect import signature
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import requests

host_target = os.environ["AIS_TARGET_URL"]
code_file = os.getenv("MOD_NAME")
arg_type = os.getenv("ARG_TYPE", "bytes")

spec = importlib.util.spec_from_file_location(
    name="function", location=f"./code/{code_file}.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

try:
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 0))
except Exception:
    CHUNK_SIZE = 0

transform = getattr(mod, os.getenv("FUNC_TRANSFORM"))


def _assert_validations():
    transform_params = len(signature(transform).parameters)
    if CHUNK_SIZE > 0 and transform_params < 2:
        raise ValueError(
            "Required to pass context as a parameter to transform if CHUNK_SIZE > 0"
        )


class StreamWrapper:
    def __init__(self, rfile, content_length, chunk_size):
        self._rfile = rfile
        self._content_length = content_length
        self._chunk_size = chunk_size
        self._remaining_length = content_length

    def read(self) -> bytes:
        return next(self)

    def read_all(self) -> bytes:
        return self._rfile.read(self._remaining_length)

    def __iter__(self) -> Iterator[bytes]:
        while self._remaining_length > 0:
            read_buffer = min(self._chunk_size, self._remaining_length)
            self._remaining_length -= read_buffer
            yield self._rfile.read(read_buffer)


class Handler(BaseHTTPRequestHandler):
    def log_request(self, *args):
        # Don't log successful requests info; log errors only.
        pass

    def _set_headers(self, content_length=None):
        """Set response headers"""
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.end_headers()

    def do_PUT(self):
        """Handles PUT requests by applying a transformation function to the request body"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            reader = StreamWrapper(self.rfile, content_length, CHUNK_SIZE)

            if CHUNK_SIZE == 0:
                result = transform(reader.read_all())
                self._set_headers(content_length=len(result))
                self.wfile.write(result)
                return

            # Streaming transform: writer is expected to write bytes to response
            self._set_headers()
            transform(reader, self.wfile)

        except Exception as e:
            self.send_error(500, f"Error processing PUT request: {e}")

    def do_GET(self):
        """Handles GET requests by fetching data, transforming it, and returning the response"""
        try:
            if self.path == "/health":
                response = b"Running"
                self._set_headers(content_length=len(response))
                self.wfile.write(response)
                return

            query_path = host_target + self.path

            if arg_type == "url":
                result = transform(query_path)
            else:
                response = requests.get(query_path)
                response.raise_for_status()  # Raise an error if request failed
                input_bytes = response.content
                result = transform(input_bytes)

            self._set_headers(content_length=len(result))
            self.wfile.write(result)

        except requests.exceptions.RequestException as e:
            self.send_error(500, f"Failed to retrieve object: {e}")
        except Exception as e:
            self.send_error(500, f"Error processing GET request: {e}")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(addr="0.0.0.0", port=80):
    server = ThreadedHTTPServer((addr, port), Handler)
    print(f"Starting HTTP server on {addr}:{port}")
    _assert_validations()
    server.serve_forever()


if __name__ == "__main__":
    run(addr="0.0.0.0", port=80)
