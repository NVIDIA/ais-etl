#!/usr/bin/env python

#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import argparse
import io
import json
import logging
import os

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import requests

from PIL import Image
from torchvision import transforms

host_target = os.environ["AIS_TARGET_URL"]
transform_format = os.environ["FORMAT"]
transform_json = os.environ["TRANSFORM"]
transform_dict = json.loads(transform_json)

# Create a list to hold the transformations
transform_list = []

# Add each transformation to the list
for transform_name, params in transform_dict.items():
    # Get the transform class from torchvision.transforms
    transform_class = getattr(transforms, transform_name)

    # Create an instance of the transform class with the specified parameters
    transform_instance = transform_class(**params)

    # Add the transform instance to the list
    transform_list.append(transform_instance)

# Combine the transformations into a single transform
transform = transforms.Compose(transform_list)


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        # Don't log successful requests info. Unsuccessful logged by log_error().
        pass

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()

    def transform_image(self, image_bytes):
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        # Convert the PIL image to a PyTorch tensor
        tensor_transform = transforms.ToTensor()
        tensor = tensor_transform(image)
        # Apply the transformation
        transformed_tensor = transform(tensor)
        # Convert the transformed tensor back to a PIL image
        pil_transform = transforms.ToPILImage()
        transformed_image = pil_transform(transformed_tensor)
        # Convert the PIL image back to bytes
        byte_arr = io.BytesIO()
        transformed_image.save(byte_arr, format=transform_format)
        # Get the byte array
        transformed_image_bytes = byte_arr.getvalue()

        return transformed_image_bytes

    def do_PUT(self):
        try:
            content_length = int(self.headers["Content-Length"])
            put_data = self.rfile.read(content_length)
            self._set_headers()
            self.wfile.write(self.transform_image(put_data))
        except Exception as e:
            logging.error("Error processing PUT request: %s", str(e))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Data processing failed")

    def do_GET(self):
        try:
            if self.path == "/health":
                self._set_headers()
                self.wfile.write(b"Running")
                return

            response = requests.get(host_target + self.path)
            self._set_headers()
            self.wfile.write(self.transform_image(response.content))
        except Exception as e:
            logging.error("Error processing GET request: %s", str(e))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Data processing failed")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(addr="localhost", port=8000):
    server = ThreadedHTTPServer((addr, port), Handler)
    print(f"Starting HTTP server on {addr}:{port}")
    server.serve_forever()


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
