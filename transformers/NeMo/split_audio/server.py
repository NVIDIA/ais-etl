#!/usr/bin/env python

import argparse
import requests
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from aistore import Client
from io import BytesIO
import json
import tarfile
import soundfile as sf
import logging

# Configure logging
# TODO: Fix logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Fetch environment variables with defaults
HOST_TARGET = os.getenv("AIS_TARGET_URL", "")
AIS_ENDPOINT = os.getenv("AIS_ENDPOINT", "http://localhost:51080")
BUCKET = os.getenv("AIS_BUCKET", "")
PREFIX = os.getenv("AIS_PREFIX", "")
EXTENSION = os.getenv("AIS_EXTENSION", "wav")

# Initialize AIS Client
ais = Client(AIS_ENDPOINT)

def get_audio_file_from_ais(audio_id: str) -> bytes:
    """Fetch the audio file from AIS."""
    try:
        url = f"{BUCKET.strip('/')}/{PREFIX.strip('/')}/{audio_id.strip('/')}.{EXTENSION}"
        # print(f"Fetching audio file from AIS: {url}")
        return ais.fetch_object_by_url(url).get().read_all()
    except Exception as e:
        print(f"Error fetching audio file for ID {audio_id}: {e}")
        raise

def trim_audio(audio_bytes, audio_format, start_time, end_time):
    """Trim audio bytes from start_time to end_time."""
    try:
        audio_buffer = BytesIO(audio_bytes)
        with sf.SoundFile(audio_buffer, mode='r') as audio_file:
            sample_rate = audio_file.samplerate
            channels = audio_file.channels
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)
            audio_file.seek(start_sample)
            trimmed_data = audio_file.read(end_sample - start_sample)
        
        trimmed_audio_buffer = BytesIO()
        with sf.SoundFile(trimmed_audio_buffer, mode='w', samplerate=sample_rate,
                          channels=channels, format=audio_format) as trimmed_file:
            trimmed_file.write(trimmed_data)
        
        # print(f"Trimmed audio from {start_time}s to {end_time}s.")
        return trimmed_audio_buffer.getvalue()
    except Exception as e:
        print(f"Error trimming audio: {e}")
        raise

def transform(input_bytes: bytes) -> bytes:
    """Transform JSONL input bytes into a tar archive of trimmed audio files."""
    jsonl_stream = BytesIO(input_bytes)
    output_tar = BytesIO()

    try:
        with tarfile.open(fileobj=output_tar, mode="w") as tar:
            for line in jsonl_stream:
                try:
                    json_object = json.loads(line.decode('utf-8').strip())
                    audio_id = json_object.get("id")
                    part = json_object.get("part")
                    audio = get_audio_file_from_ais(audio_id)
                    transformed_audio = trim_audio(audio, "wav", json_object.get("from_time"), json_object.get("to_time"))
                    
                    audio_file = BytesIO(transformed_audio)
                    audio_file_name = f"{audio_id}_{part}.wav"
                    tarinfo = tarfile.TarInfo(name=audio_file_name)
                    tarinfo.size = len(transformed_audio)
                    tar.addfile(tarinfo, audio_file)
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON line: {e}")
                except Exception as e:
                    print(f"Error processing audio ID {json_object.get('id', 'unknown')}: {e}")

        output_tar.seek(0)
        logging.info("Transformation to tar archive complete.")
        return output_tar.getvalue()
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise

class RequestHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests."""
    def log_request(self, code="-", size="-"):
        pass

    def _set_headers(self, content_length=None, content_type="application/octet-stream"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.end_headers()

    def do_PUT(self):
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            output_bytes = transform(post_data)
            self._set_headers(content_length=len(output_bytes))
            self.wfile.write(output_bytes)
        except Exception as e:
            print(f"Error in PUT request: {e}")
            self.send_error(500, f"Internal Server Error: {e}")

    def do_GET(self):
        if self.path == "/health":
            response = b"Running"
            self._set_headers(content_length=len(response), content_type="text/plain")
            self.wfile.write(response)
            return

        try:
            response = requests.get(HOST_TARGET + self.path)
            response.raise_for_status()
            output_bytes = transform(response.content)
            self._set_headers(content_length=len(output_bytes))
            self.wfile.write(output_bytes)
        except requests.HTTPError as http_err:
            print(f"HTTP error in GET request: {http_err}")
            self.send_error(502, f"Bad Gateway: {http_err}")
        except Exception as e:
            print(f"Error in GET request: {e}")
            self.send_error(500, f"Internal Server Error: {e}")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def run_server(addr="localhost", port=8000):
    """Start the threaded HTTP server."""
    print(f"Starting HTTP server on {addr}:{port}")
    server = ThreadedHTTPServer((addr, port), RequestHandler)
    server.serve_forever()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple HTTP server.")
    parser.add_argument("-l", "--listen", default="localhost", help="IP address to listen on.")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to listen on.")
    args = parser.parse_args()
    run_server(addr=args.listen, port=args.port)
