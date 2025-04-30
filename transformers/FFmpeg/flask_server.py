"""
FFmpeg ETL Transformer (Flask)

This module implements an ETL transformer as a FastAPI-based server
that transform audio files into WAV format with control over
Audio Channels (`AC`) and Audio Rate (`AR`) with help of FFmpeg utility.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import subprocess

from aistore.sdk.etl.webserver import FlaskServer


class FFmpegServer(FlaskServer):
    """
    Flask-based server for FFmpeg-based ETL transformation.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        super().__init__(host=host, port=port)
        # configure from environment or defaults
        self.channels = os.getenv("AC", "1")
        self.samplerate = os.getenv("AR", "44100")
        # base ffmpeg command, reading from stdin, writing WAV to stdout
        self.ffmpeg_cmd = [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-ac",
            self.channels,
            "-ar",
            self.samplerate,
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            "pipe:1",
        ]
        self.audio_exts = {".wav", ".flac", ".mp3", ".m4a", ".opus", ".ogg"}

    def transform(self, data: bytes, path: str) -> bytes:
        """
        Run FFmpeg to convert raw audio into WAV format.
        Raises an error on FFmpeg failure.
        """
        ext = os.path.splitext(path)[1].lower()
        # If it doesn’t look like audio, just pass it back without processing it
        if ext not in self.audio_exts:
            return data

        with subprocess.Popen(
            self.ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            out, err = proc.communicate(input=data)
            if proc.returncode != 0:
                msg = err.decode("utf-8", errors="ignore").strip()
                self.logger.error("FFmpeg error: %s", msg)
                raise RuntimeError(f"FFmpeg process failed: {msg}")
            return out

    def get_mime_type(self) -> str:
        """
        Return the MIME type for the transformed data.
        """
        return "audio/wav"


flask_server = FFmpegServer(port=8000)
flask_server.logger.setLevel("DEBUG")
flask_app = flask_server.app
