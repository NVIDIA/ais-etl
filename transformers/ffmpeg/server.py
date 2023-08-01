#!/usr/bin/env python

#
# Copyright (c) 2022-2023, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-docstring, invalid-name

import argparse
import json
import logging
import os

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import ffmpeg
import filetype
import requests


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.host_target = os.environ["AIS_TARGET_URL"]
        self.ffmpeg_options = json.loads(os.environ["FFMPEG_OPTIONS"])

        if not self.ffmpeg_options or not isinstance(self.ffmpeg_options, dict):
            raise ValueError("FFMPEG_OPTIONS must be a valid JSON dictionary")

        self.ffmpeg_format = self.ffmpeg_options.get("format")
        super().__init__(*args, **kwargs)

    def log_request(self, code="-", size="-"):
        pass

    def handle_error(self, error_message):
        logging.error(error_message)
        self.send_response(500)
        self.end_headers()
        self.wfile.write(b"Data processing failed")

    def _set_headers(self, content_type):
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}")
        self.end_headers()

    def process_data(self, data):
        input_stream = ffmpeg.input("pipe:0")
        output_stream = ffmpeg.output(input_stream, "pipe:1", **self.ffmpeg_options)
        try:
            output, _ = ffmpeg.run(
                output_stream, input=data, capture_stdout=True, capture_stderr=True
            )
            self.wfile.write(output)
        except ffmpeg.Error as error:
            self.handle_error(f"FFMPEG Error: {error.stderr.decode()}")

    def handle_request(self, data):
        if self.ffmpeg_format:
            self._set_headers(content_type=f"audio/{self.ffmpeg_format}")
        else:
            input_type = filetype.guess(data)
            self._set_headers(content_type=str(input_type.mime))
            self.ffmpeg_options["format"] = input_type.extension

        self.process_data(data)

    def do_PUT(self):
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            self.handle_request(post_data)
        except Exception as error:
            self.handle_error(f"Error processing PUT request: {str(error)}")

    def do_GET(self):
        try:
            if self.path == "/health":
                self._set_headers(content_type="text/plain")
                self.wfile.write(b"OK")
                return

            response = requests.get(self.host_target + self.path, timeout=3.05)
            self.handle_request(response.content)
        except Exception as error:
            self.handle_error(f"Error processing GET request: {str(error)}")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


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
        required=False,
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        required=False,
        help="Specify the port on which the server listens",
    )
    parser_args = parser.parse_args()
    run(addr=parser_args.listen, port=parser_args.port)
