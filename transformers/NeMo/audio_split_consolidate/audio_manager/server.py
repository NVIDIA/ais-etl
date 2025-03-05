#!/usr/bin/env python
"""
Audio Manager creates archive (tar) for each metadata file and triggers ETL
to split audio files based on "from_time" and "to_time" metadata.
"""

import argparse
import json
import logging
import os
import tarfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from socketserver import ThreadingMixIn
from typing import Optional, Dict, Any

from aistore import Client
from aistore.sdk.etl import ETLConfig
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Configuration using environment variables with validation
class Config:
    def __init__(self):
        self.host_target = os.getenv("AIS_TARGET_URL")
        self.ais_endpoint = os.getenv("AIS_ENDPOINT")
        self.bucket = os.getenv("SRC_BUCKET")
        self.provider = os.getenv("SRC_PROVIDER", "ais")
        self.prefix = os.getenv("OBJ_PREFIX", "")
        self.extension = os.getenv("OBJ_EXTENSION", "wav")
        self.etl_name = os.getenv("ETL_NAME")
        self.direct_from_target = os.getenv(
            "DIRECT_FROM_TARGET", "true"
        ).strip().lower() in ("true", "1", "yes")
        max_pool_size_str = os.getenv("MAX_POOL_SIZE")
        try:
            self.max_pool_size = (
                int(max_pool_size_str) if max_pool_size_str is not None else 50
            )
        except ValueError:
            logging.error(
                "Invalid MAX_POOL_SIZE value '%s'. Falling back to default (50).",
                max_pool_size_str,
            )
            self.max_pool_size = 50

        if not self.bucket:
            raise ValueError("SRC_BUCKET environment variable is required")
        if not self.etl_name:
            raise ValueError("ETL_NAME environment variable is required")
        if not self.host_target:
            raise ValueError("AIS_TARGET_URL environment variable is required")
        if not self.ais_endpoint:
            raise ValueError("AIS_ENDPOINT environment variable is required")


# Initialize configuration and client
try:
    config = Config()
    client = Client(config.ais_endpoint, max_pool_size=config.max_pool_size)
    src_bucket = client.bucket(bck_name=config.bucket, provider=config.provider)
except ValueError as e:
    logger.critical("Configuration error: %s", e)
    exit(1)
except Exception as e:
    logger.critical("Initialization failed: %s", e)
    exit(1)


def fetch_transformed_audio(data: dict) -> bytes:
    """Retrieve transformed audio file from AIS using ETL."""
    try:
        audio_id = data.get("id")
        obj_path = f"{config.prefix}{audio_id}.{config.extension}"
        etl_args = json.dumps(data)  # Serialize args for better logging
        logger.info(
            "Fetching transformed audio: path=%s, etl_args=%s", obj_path, etl_args
        )

        obj = src_bucket.object(obj_path)
        return obj.get_reader(
            etl=ETLConfig(config.etl_name, args=data), direct=config.direct_from_target
        ).read_all()
    except Exception as e:
        logger.exception(
            "Error fetching transformed audio for ID %s: %s", audio_id, str(e)
        )
        raise


def process_json_line(line: str) -> Optional[Dict[str, Any]]:
    """Process a single JSON line and return parsed data."""
    try:
        data = json.loads(line.strip())
        if not all(key in data for key in ("id", "part", "from_time", "to_time")):
            logger.warning("Missing required fields in JSON line: %s", line)
            return None
        return data
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON line: %s - Error: %s", line, e)
        return None


def create_tar_archive(input_bytes: bytes) -> bytes:
    """Create tar archive from JSONL input containing audio processing instructions."""
    output_tar = BytesIO()
    processed_count = 0

    try:
        with tarfile.open(fileobj=output_tar, mode="w") as tar:
            for line_number, line in enumerate(input_bytes.decode().splitlines(), 1):
                if not line.strip():
                    continue

                if (data := process_json_line(line)) is None:
                    logger.info("Skipping invalid line %d : %s", line_number, line)
                    continue

                try:
                    audio_content = fetch_transformed_audio(data)
                    tar_info = tarfile.TarInfo(name=f"{data['id']}_{data['part']}.wav")
                    tar_info.size = len(audio_content)
                    tar.addfile(tar_info, BytesIO(audio_content))
                    processed_count += 1

                except Exception as e:
                    logger.error("Failed to process line %d: %s", line_number, e)

        # logger.info("Created tar archive with %d audio files", processed_count)
        return output_tar.getvalue()
    except Exception as e:
        logger.error("Tar creation failed: %s", e)
        raise


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler with improved error handling."""

    def log_request(self, code="-", size="-"):
        pass

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

    def do_PUT(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_response(400, b"Empty request body")
                return

            input_data = self.rfile.read(content_length)
            tar_data = create_tar_archive(input_data)
            self._send_response(200, tar_data)

        except Exception as e:
            logger.error("PUT request failed: %s", e)
            self._send_response(500, f"Internal Server Error: {e}".encode())

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_response(200, b"OK", "text/plain")
            return

        try:
            response = requests.get(f"{config.host_target}{self.path}", timeout=60)
            response.raise_for_status()
            tar_data = create_tar_archive(response.content)
            self._send_response(200, tar_data)

        except requests.RequestException as e:
            logger.error("GET request failed: %s", e)
            self._send_response(502, f"Bad Gateway: {e}".encode())
        except Exception as e:
            logger.error("GET processing failed: %s", e)
            self._send_response(500, f"Internal Server Error: {e}".encode())


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling concurrent requests."""

    daemon_threads = True


def run_server(host: str = "localhost", port: int = 8000) -> None:
    """Start the HTTP server with proper shutdown handling."""
    server = ThreadedHTTPServer((host, port), HTTPRequestHandler)
    logger.info("Starting server on %s:%d", host, port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio Processing HTTP Server")
    parser.add_argument("-l", "--listen", default="localhost", help="Bind address")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Listen port")
    args = parser.parse_args()

    try:
        run_server(args.listen, args.port)
    except Exception as e:
        logger.critical("Server failed: %s", e)
        exit(1)
