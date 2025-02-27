#!/usr/bin/env python
# Transform (split) audio files based on metadata

import argparse
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from socketserver import ThreadingMixIn
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs, unquote_plus
import json

import requests
import soundfile as sf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

HOST_TARGET = os.getenv("AIS_TARGET_URL", "http://localhost:51081")


def trim_audio(
    audio_bytes: bytes, audio_format: str, start_time: float, end_time: float
) -> Optional[bytes]:
    """Trim audio bytes from start_time to end_time."""
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


def transform(data: bytes, etl_args: Dict[str, str]) -> Optional[bytes]:
    """Transform the audio data based on metadata."""
    try:
        from_time = float(etl_args["from_time"])
        to_time = float(etl_args["to_time"])
        audio_format = etl_args.get("audio_format", "wav")
        transformed_audio = trim_audio(data, audio_format, from_time, to_time)
        return transformed_audio
    except Exception as e:
        logging.error("Error during transformation: %s", e)
        raise


class RequestHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests."""

    def log_request(self, code="-", size="-"):
        pass

    def _parse_etl_args(self) -> Optional[Dict[str, str]]:
        """Extract and validate etl_args from the query string."""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        etl_args_encoded = query_params.get("etl_args", [None])[0]
        if etl_args_encoded is None:
            logging.error("Missing 'etl_args' query parameter")
            self.send_error(400, "Missing required 'etl_args' parameter")
            return None

        etl_args_decoded = unquote_plus(etl_args_encoded)
        try:
            etl_args = json.loads(etl_args_decoded)
        except json.JSONDecodeError:
            logging.error("Invalid etl_args JSON format: %s", etl_args_decoded)
            self.send_error(400, "Invalid etl_args format")
            return None

        if "from_time" not in etl_args or "to_time" not in etl_args:
            logging.error("Missing required etl_args keys: 'from_time' and 'to_time'")
            self.send_error(
                400, "Missing required etl_args keys: 'from_time' and 'to_time'"
            )
            return None

        return etl_args

    def _send_response(
        self,
        status: int,
        content: bytes = b"",
        content_type: str = "application/octet-stream",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if content:
            self.wfile.write(content)

    def do_GET(self):
        if self.path == "/health":
            response = b"Running"
            self._send_response(200, response, "text/plain")
            self.wfile.write(response)
            return

        logging.info("Processing GET request for path: %s", self.path)

        etl_args = self._parse_etl_args()
        if etl_args is None:
            return  # Error already handled in _parse_etl_args

        try:
            query_path = HOST_TARGET + urlparse(self.path).path
            data = requests.get(query_path, timeout=120).content
            output_bytes = transform(data, etl_args=etl_args)
            logging.info("Transformation completed for: %s", query_path)
            self._send_response(200, output_bytes)
        except requests.HTTPError as http_err:
            logging.error("HTTP error in GET request: %s", http_err)
            self.send_error(502, f"Bad Gateway: {http_err}")
        except Exception as e:
            logging.error("Error in GET request: %s", e)
            self.send_error(500, f"Internal Server Error: {e}")

    def do_PUT(self):
        logging.info("Processing PUT request for path: %s", self.path)
        etl_args = self._parse_etl_args()
        if etl_args is None:
            return  # Error already handled in _parse_etl_args

        try:
            # Read incoming data from the request body
            content_length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(content_length) if content_length > 0 else b""
            if not data:
                logging.error("No data received in PUT request")
                self.send_error(400, "No data received")
                return

            output_bytes = transform(data, etl_args=etl_args)
            logging.info(
                "Transformation and PUT forwarding completed for: %s", self.path
            )
            self._send_response(200, output_bytes)
        except requests.HTTPError as http_err:
            logging.error("HTTP error in PUT request: %s", http_err)
            self.send_error(502, f"Bad Gateway: {http_err}")
        except Exception as e:
            logging.error("Error in PUT request: %s", e)
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
