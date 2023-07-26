#!/usr/bin/env python

#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import argparse
import requests
import os
import gzip
import bz2
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

host_target = os.environ['AIS_TARGET_URL']

class Handler(BaseHTTPRequestHandler):
    # Overriding log_request to not log successful requests
    def log_request(self, code='-', size='-'):
        pass

    # Set standard headers for responses
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()

    # Method to process incoming data, supporting both compression and decompression, and
    # gzip and bz2 compression algorithms
    def process_data(self, data):
        try:
            if args.mode == 'compress':
                if args.compression == 'gzip':
                    return gzip.compress(data)
                elif args.compression == 'bz2':
                    return bz2.compress(data)
                else:
                    raise ValueError(f"Unsupported compression algorithm: {args.compression}")
            elif args.mode == 'decompress':
                if args.compression == 'gzip':
                    return gzip.decompress(data)
                elif args.compression == 'bz2':
                    return bz2.decompress(data)
                else:
                    raise ValueError(f"Unsupported compression algorithm: {args.compression}")
            else:
                raise ValueError(f"Unsupported data processing mode: {args.mode}")
        except Exception as e:
            # Log the error for debugging
            print(f"Error during data processing: {e}")
            # Return None to indicate a failure
            return None     

    # PUT handler supports `hpush` operation
    def do_PUT(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        processed_data = self.process_data(post_data)
        if processed_data is not None:
            self._set_headers()
            self.wfile.write(processed_data)
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Data processing failed") 

    # GET handler supports `hpull` operation
    def do_GET(self):
        if self.path == "/health":
            self._set_headers()
            self.wfile.write(b"OK")
            return

        response = requests.get(host_target + self.path)
        processed_data = self.process_data(response.content)
        
        if processed_data is not None:
            self._set_headers()
            self.wfile.write(processed_data)
        else:
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
        "-l", "--listen",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        help="Specify the port on which the server listens",
    )
    parser.add_argument(
        "--compression",
        default="gzip",
        help="Specify the compression algorithm to use (e.g. gzip, bz2)",
    )
    parser.add_argument(
        "--mode",
        default="compress",
        help="Specify the data processing mode to use (e.g. 'compress' or 'decompress')",
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port)
