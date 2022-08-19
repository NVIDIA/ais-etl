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

FIRST_CHUNK_SIZE_FILTER = 8192

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
        object_name = self.path

        if FILTER_EXISTS:
            # retreive first chunk
            first_chunk_size = FIRST_CHUNK_SIZE_FILTER

            if CHUNK_SIZE > 0:
                first_chunk_size = CHUNK_SIZE

            first_chunk_size = min(first_chunk_size, content_length)
            first_chunk = self.rfile.read(first_chunk_size)

            if not filter(object_name, first_chunk):
                self.send_response_only(204)  # or 200
                self.end_headers()
                return

            content_length -= first_chunk_size
        else:
            first_chunk = b""

        # populate context
        context = {}

        if BEFORE_EXISTS:
            before(context)

        self._set_headers()
        if CHUNK_SIZE == 0:
            print("here")
            input_bytes = (
                first_chunk
                if content_length == 0
                else (first_chunk + self.rfile.read(content_length))
            )
            print("ip", input_bytes[:5])
            context["result"] = (
                transform(input_bytes, context)
                if len(signature(transform).parameters) > 1
                else transform(input_bytes)
            )
            print("op", context["result"][:5])
        else:
            context["transformed-length"] = 0
            context["remaining-length"] = content_length

            if FILTER_EXISTS and len(first_chunk) != 0:
                output = transform(first_chunk, context)
                if output is not None:
                    self.wfile.write(output)
                context["transformed-length"] += first_chunk_size

            while context["remaining-length"] > 0:
                read_buffer_size = (
                    CHUNK_SIZE
                    if context["remaining-length"] >= CHUNK_SIZE
                    else context["remaining-length"]
                )

                # if transform functions returns anything return it back to user
                output = transform(self.rfile.read(read_buffer_size), context)

                if output is not None:
                    self.wfile.write(output)

                context["transformed-length"] += read_buffer_size
                context["remaining-length"] -= read_buffer_size

        if AFTER_EXISTS:
            context["result"] = after(context)

        if "result" in context and context["result"] != None:
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
    run(addr="0.0.0.0", port=80)
