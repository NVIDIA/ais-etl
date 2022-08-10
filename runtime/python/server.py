#!/usr/bin/env python

import os
import sys
import imp
import requests
if sys.version_info[0] < 3:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SocketServer import ThreadingMixIn
else:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from socketserver import ThreadingMixIn

DEFAULT_CHUNK_SIZE = 32768

host_target = os.environ["AIS_TARGET_URL"]

mod = imp.load_source("function", "./code/%s.py" % os.getenv("MOD_NAME"))
try:
    before = getattr(mod, os.getenv("FUNC_BEFORE"))
except AttributeError:
    def before():
        pass

transform = getattr(mod, os.getenv("FUNC_TRANSFORM"))
after = getattr(mod, os.getenv("FUNC_AFTER"))


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
        
        arg = before()

        while (content_length > 0):
            read_buffer = DEFAULT_CHUNK_SIZE if content_length > DEFAULT_CHUNK_SIZE else content_length
            transform(self.rfile.read(read_buffer), arg)
            content_length -= read_buffer

        result = after(arg)
        self._set_headers()
        self.wfile.write(result)

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
    print("Starting HTTP server on {}:{}".format(addr, port))
    server.serve_forever()


if __name__ == "__main__":
    run(addr="0.0.0.0", port=80)
