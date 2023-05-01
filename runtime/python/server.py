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

spec = importlib.util.spec_from_file_location(name="function", location=f"./code/{code_file}.py")
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
            read_buffer = (
                self._chunk_size
                if self._remaining_length >= self._chunk_size
                else self._remaining_length
            )
            self._remaining_length -= read_buffer
            yield self._rfile.read(read_buffer)


class Handler(BaseHTTPRequestHandler):
    def log_request(self, *args):
        # Don't log successful requests info. Unsuccessful logged by log_error().
        pass

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()

    def do_PUT(self):
        content_length = int(self.headers["Content-Length"])
        reader = StreamWrapper(self.rfile, content_length, CHUNK_SIZE)
        if CHUNK_SIZE == 0:
            result = transform(reader.read_all())
            self._set_headers()
            self.wfile.write(result)
            return

        # TODO: validate if transform takes writer as input
        # NOTE: for streaming transforms the writer is expected to write bytes into response as stream.
        self._set_headers()
        transform(reader, self.wfile)

    def do_GET(self):
        if self.path == "/health":
            self._set_headers()
            self.wfile.write(b"OK")
            return
        
        query_path = host_target + self.path

        if arg_type == "url":
            result = transform(query_path)
        else:
            input_bytes = requests.get(query_path).content
            result = transform(input_bytes)

        self._set_headers()
        self.wfile.write(result)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(addr="0.0.0.0", port=80):
    server = ThreadedHTTPServer((addr, port), Handler)
    print(f"Starting HTTP server on {addr}:{port}")
    _assert_validations()
    server.serve_forever()


if __name__ == "__main__":
    run(addr="0.0.0.0", port=80)
