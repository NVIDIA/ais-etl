#!/usr/bin/env python

import argparse
import requests
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import subprocess
import io
import wave
from urllib.parse import unquote

# Fetch environment variables with defaults
HOST_TARGET = os.getenv("AIS_TARGET_URL", "")
AR = int(os.getenv("AR", 44100))
AC = int(os.getenv("AC", 1))
ARG_TYPE = os.getenv("ARG_TYPE", "").lower()


# Define the transform function for audio processing
def transform(input_bytes: bytes, ac: int = AC, ar: int = AR) -> bytes:
    process_args = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-map",
        "0:a",
        "-ac",
        str(ac),
        "-ar",
        str(ar),
        "-c:a",
        "pcm_s16le",
        "-f",
        "s16le",  # Output raw PCM data
        "-y",
        "pipe:1",
    ]

    # Run ffmpeg and capture raw PCM data
    process = subprocess.Popen(
        process_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    raw_audio_data, stderr = process.communicate(input=input_bytes)

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg process failed: {stderr.decode()}")

    # Create a WAV file in memory
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(ac)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(ar)
            wav_file.writeframes(raw_audio_data)
        output_bytes = wav_io.getvalue()

    return output_bytes


class RequestHandler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        # Suppress request logs; error logs will be handled separately
        pass

    def _set_headers(self, content_length=None, content_type="audio/wav"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.end_headers()

    def do_PUT(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        try:
            output_bytes = transform(post_data)
            self._set_headers(content_length=len(output_bytes))
            self.wfile.write(output_bytes)
        except RuntimeError as error:
            self.send_error(500, str(error))

    def do_GET(self):
        if self.path == "/health":
            response = b"Running"
            self._set_headers(content_length=len(response), content_type="text/plain")
            self.wfile.write(response)
            return

        try:
            if ARG_TYPE == "fqn":
                decoded_path = unquote(self.path)
                safe_path = os.path.normpath(
                    os.path.join("/", decoded_path.lstrip("/"))
                )
                with open(safe_path, "rb") as file:
                    file_content = file.read()
                output_bytes = transform(file_content)
            else:
                response = requests.get(HOST_TARGET + self.path)
                response.raise_for_status()
                output_bytes = transform(response.content)
            self._set_headers(content_length=len(output_bytes))
            self.wfile.write(output_bytes)
        except requests.HTTPError as http_err:
            self.send_error(502, f"Error fetching data: {http_err}")
        except RuntimeError as error:
            self.send_error(500, str(error))


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run_server(addr="localhost", port=8000):
    server = ThreadedHTTPServer((addr, port), RequestHandler)
    print(f"Starting HTTP server on {addr}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-l", "--listen", default="localhost", help="IP address to listen on"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8000, help="Port to listen on"
    )
    args = parser.parse_args()
    run_server(addr=args.listen, port=args.port)
