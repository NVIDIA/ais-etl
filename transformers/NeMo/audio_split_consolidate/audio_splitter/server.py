#!/usr/bin/env python
# Transform (split) audio files based on metadata

# Standard library imports
import argparse
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from socketserver import ThreadingMixIn
from typing import Dict, Optional, Tuple

# Third-party imports
import requests
import soundfile as sf
from aistore.sdk.obj.object_attributes import ObjectAttributes


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

HOST_TARGET = os.getenv("AIS_TARGET_URL", "http://localhost:51081")


def trim_audio(
    audio_bytes: bytes, audio_format: str, start_time: float, end_time: float
) -> Optional[bytes]:
    """Trim audio bytes from start_time to end_times"""
    try:
        logging.info(
            "Trimming audio from %s to %s in %s format",
            start_time,
            end_time,
            audio_format,
        )
        audio_buffer = BytesIO(audio_bytes)
        with sf.SoundFile(audio_buffer, mode="r") as audio_file:
            sample_rate = audio_file.samplerate
            channels = audio_file.channels
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)
            audio_file.seek(start_sample)
            trimmed_data = audio_file.read(end_sample - start_sample)
        trimmed_audio_buffer = BytesIO()
        with sf.SoundFile(
            trimmed_audio_buffer,
            mode="w",
            samplerate=sample_rate,
            channels=channels,
            format=audio_format,
        ) as trimmed_file:
            trimmed_file.write(trimmed_data)
        logging.info("Audio trimming completed")
        return trimmed_audio_buffer.getvalue()
    except Exception as e:
        logging.error("Error trimming audio: %s", e)
        raise


def query_ais(query_path: str) -> Tuple[bytes, Dict[str, str]]:
    """Query AIStore for the object and extract metadata."""
    try:
        logging.info("Querying AIStore at path: %s", query_path)
        resp = requests.get(query_path, timeout=120)
        resp.raise_for_status()
        data = resp.content
        metadata = ObjectAttributes(resp.headers).custom_metadata
        logging.info("Received metadata: %s", metadata)
        return data, metadata
    except requests.RequestException as e:
        logging.error("Error querying AIStore: %s", e)
        raise


def transform(data: bytes, metadata: Dict[str, str]) -> Optional[bytes]:
    """Transform the audio data based on metadata."""
    try:
        from_time = float(metadata.get("from_time", 0))
        to_time = float(metadata.get("to_time", 0))
        audio_format = metadata.get("audio_format", "wav")
        transformed_audio = trim_audio(data, audio_format, from_time, to_time)
        return transformed_audio
    except KeyError as e:
        logging.error("Missing key in metadata: %s", e)
        raise
    except Exception as e:
        logging.error("Error during transformation: %s", e)
        raise


class RequestHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests."""

    def log_request(self, code="-", size="-"):
        # logging.info(
        #     "Request: %s %s - Code: %s, Size: %s", self.command, self.path, code, size
        # )
        pass

    def _set_headers(
        self, content_length=None, content_type="application/octet-stream"
    ):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            response = b"Running"
            self._set_headers(content_length=len(response), content_type="text/plain")
            self.wfile.write(response)
            return

        try:
            query_path = HOST_TARGET + self.path
            logging.info("Processing GET request for path: %s", self.path)
            data, metadata = query_ais(query_path)
            logging.info("Transforming audio: %s", self.path)
            output_bytes = transform(data, metadata)
            logging.info("Transformation completed for audio: %s", self.path)
            self._set_headers(content_length=len(output_bytes))
            self.wfile.write(output_bytes)
        except requests.HTTPError as http_err:
            logging.error("HTTP error in GET request: %s", http_err)
            self.send_error(502, f"Bad Gateway: {http_err}")
        except Exception as e:
            logging.error("Error in GET request: %s", e)
            self.send_error(500, f"Internal Server Error: {e}")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run_server(addr="localhost", port=8000):
    """Start the threaded HTTP server."""
    logging.info("Starting HTTP server on %s:%s", addr, port)
    try:
        server = ThreadedHTTPServer((addr, port), RequestHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down the server.")
    except Exception as e:
        logging.error("Unexpected server error: %s", e)
    finally:
        logging.info("Server stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple HTTP server.")
    parser.add_argument(
        "-l", "--listen", default="localhost", help="IP address to listen on."
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8000, help="Port to listen on."
    )
    args = parser.parse_args()
    run_server(addr=args.listen, port=args.port)
