#!/usr/bin/env python

import argparse
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import os


host_target = os.environ['AIS_TARGET_URL']

class S(BaseHTTPRequestHandler):
    def _set_headers(self,headers={}):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        for k in headers:
            self.send_header(k, headers[k])
        self.end_headers()

    def do_PUT(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        md5 = hashlib.md5()
        md5.update(post_data)
        self._set_headers({"Content-MD5":md5.hexdigest()})
        self.wfile.write(post_data)

    def do_GET(self):
        global host_target
        x = requests.get(host_target + "/v1/objects" + self.path)
        md5 = hashlib.md5()
        md5.update(x.content)
        self._set_headers({"Content-MD5":md5.hexdigest()})
        self.wfile.write(x.content)


def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()


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
