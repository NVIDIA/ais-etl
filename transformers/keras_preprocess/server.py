#!/usr/bin/env python
#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import os
import json
import logging
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import io
from keras.preprocessing.image import (
    ImageDataGenerator,
    load_img,
    array_to_img,
    img_to_array,
)

# Constants
FORMAT = os.getenv("FORMAT", "JPEG")
ARG_TYPE = os.getenv("ARG_TYPE", "bytes")

# Environment Variables
host_target = os.environ.get("AIS_TARGET_URL")
TRANSFORM = os.environ.get("TRANSFORM")
if not host_target:
    raise EnvironmentError("AIS_TARGET_URL environment variable missing")
if not TRANSFORM:
    raise EnvironmentError(
        "TRANSFORM environment variable missing. Check documentation for examples (link)"
    )
transform_dict = json.loads(TRANSFORM)


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        """Override log_request to not log successful requests."""
        pass

    def _set_headers(self):
        """Set standard headers for responses."""
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()

    def transform(self, data: bytes) -> bytes:
        """Process image data as bytes using the specified transformation."""
        try:
            img = load_img(io.BytesIO(data))
            img = img_to_array(img)
            datagen = ImageDataGenerator()
            img = datagen.apply_transform(x=img, transform_parameters=transform_dict)
            img = array_to_img(img)
            buf = io.BytesIO()
            img.save(buf, format=FORMAT)
            return buf.getvalue()
        except Exception as e:
            logging.error("Error processing data: %s", str(e))
            raise

    def do_PUT(self):
        """PUT handler supports `hpush` operation."""
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            processed_data = self.transform(post_data)
            if processed_data is not None:
                self._set_headers()
                self.wfile.write(processed_data)
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Data processing failed")
        except Exception as e:
            logging.error("Error processing PUT request: %s", str(e))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Data processing failed")

    def do_GET(self):
        """GET handler supports `hpull` operation."""
        try:
            if self.path == "/health":
                self._set_headers()
                self.wfile.write(b"OK")
                return

            query_path = host_target + self.path

            if ARG_TYPE == "url":  # need this for webdataset
                result = self.transform(query_path)
            else:
                input_bytes = requests.get(query_path).content
                result = self.transform(input_bytes)

            if result is not None:
                self._set_headers()
                self.wfile.write(result)
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Data processing failed")
        except Exception as e:
            logging.error("Error processing GET request: %s", str(e))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Data processing failed")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(addr="0.0.0.0", port=80):
    server = ThreadedHTTPServer((addr, port), Handler)
    logging.info(f"Starting HTTP server on {addr}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run(addr="0.0.0.0", port=80)
