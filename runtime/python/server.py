#!/usr/bin/env python

import os
import sys
import imp
import requests
from inspect import signature

if sys.version_info[0] < 3:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SocketServer import ThreadingMixIn
else:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from socketserver import ThreadingMixIn

host_target = os.environ["AIS_TARGET_URL"]
code_file = os.getenv("MOD_NAME")
mod = imp.load_source("function", f"./code/{code_file}.py")

try:
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE"))
except Exception:
    CHUNK_SIZE = 0

try:
    before = getattr(mod, os.getenv("FUNC_BEFORE"))
    BEFORE_EXISTS = True
except Exception:
    BEFORE_EXISTS = False

try:
    after = getattr(mod, os.getenv("FUNC_AFTER"))
    AFTER_EXISTS = True
except Exception:
    AFTER_EXISTS = False

try:
    filter = getattr(mod, os.getenv("FUNC_FILTER"))
    FILTER_EXISTS = True
except Exception:
    FILTER_EXISTS = False

transform = getattr(mod, os.getenv("FUNC_TRANSFORM"))


def _assert_validations():
    transform_params = len(signature(transform).parameters)
    if CHUNK_SIZE > 0 and transform_params < 2:
        raise ValueError(
            "Required to pass context as a parameter to transform if CHUNK_SIZE > 0"
        )

    if (BEFORE_EXISTS or AFTER_EXISTS) and transform_params < 2:
        raise ValueError(
            "Required to pass context as a parameter to transform if before() or after() exists"
        )


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

        # TODO: handle filters
        # if FILTER_EXISTS and not filter(self.headers["Name"], content_length):
        # self._set_headers()

        # populate context
        context = {}

        if BEFORE_EXISTS:
            before(context)

        if CHUNK_SIZE == 0:
            params = len(signature(transform).parameters)
            context["result"] = (
                transform(self.rfile.read(content_length), context)
                if params > 1
                else transform(self.rfile.read(content_length))
            )
        else:
            context["transformed-length"] = 0
            context["remaining-length"] = content_length
            while context["remaining-length"] > 0:
                read_buffer = (
                    CHUNK_SIZE
                    if context["remaining-length"] >= CHUNK_SIZE
                    else context["remaining-length"]
                )
                # user expected to store partial result in context
                transform(self.rfile.read(read_buffer), context)
                context["transformed-length"] += read_buffer
                context["remaining-length"] -= read_buffer

        if AFTER_EXISTS:
            context["result"] = after(context)
        self._set_headers()
        self.wfile.write(context["result"])

    def do_GET(self):
        if self.path == "/health":
            self._set_headers()
            self.wfile.write(b"OK")
            return

        input_bytes = requests.get(host_target + self.path)
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
    run(addr="0.0.0.0", port=50051)
