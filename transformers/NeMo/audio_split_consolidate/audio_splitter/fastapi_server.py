"""
Audio Splitter ETL Server

This FastAPI-based ETL server reads raw audio bytes from the request payload,
trims each audio stream according to `from_time` and `to_time` parameters provided
via the `etl_args` query parameter (JSON-encoded), and returns the trimmed audio
in the specified format.

Example request:
    GET /path/to/audio?etl_args={"from_time":1.5,"to_time":3.0,"audio_format":"flac"}

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import json
from io import BytesIO
from typing import Any, Dict
from urllib.parse import unquote_plus

import soundfile as sf
from fastapi import HTTPException
from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class AudioSplitterServer(FastAPIServer):
    """
    ETL server that trims incoming audio streams.

    transform() signature:
        transform(data: bytes, path: str, etl_args: str) -> bytes

    `etl_args` must be a JSON string containing:
      - from_time: float (start in seconds)
      - to_time:   float (end in seconds)
      - audio_format: Optional[str] (e.g. "wav", "flac")
    """

    def __init__(self, port: int = 8000) -> None:
        super().__init__(port=port)
        self.logger.setLevel("DEBUG")
        self.logger.info("AudioSplitterServer initialized on port %d", port)

    def _parse_etl_args(self, raw: str) -> Dict[str, Any]:
        """
        Decode and validate the `etl_args` JSON string.

        Raises:
            HTTPException(400): if missing or invalid JSON or required keys.
        """
        if not raw:
            raise HTTPException(400, "Missing required query parameter 'etl_args'")
        try:
            decoded = unquote_plus(raw)
            args = json.loads(decoded)
        except Exception as e:
            self.logger.error("Failed to decode etl_args: %s", e)
            raise HTTPException(400, "Invalid etl_args JSON") from e

        if "from_time" not in args or "to_time" not in args:
            msg = "etl_args must include 'from_time' and 'to_time'"
            self.logger.error(msg)
            raise HTTPException(400, msg)

        return args

    def _trim_audio(
        self, audio_bytes: bytes, start_time: float, end_time: float, fmt: str
    ) -> bytes:
        """
        Trim the given audio bytes between start_time and end_time.

        Uses `soundfile` to read/write audio in memory.
        """
        buf_in = BytesIO(audio_bytes)
        try:
            with sf.SoundFile(buf_in, mode="r") as reader:
                sr = reader.samplerate
                ch = reader.channels
                start = int(start_time * sr)
                length = int((end_time - start_time) * sr)
                reader.seek(start)
                data = reader.read(frames=length, dtype="int16")

            buf_out = BytesIO()
            with sf.SoundFile(
                buf_out,
                mode="w",
                samplerate=sr,
                channels=ch,
                format=fmt,
            ) as writer:
                writer.write(data)

            return buf_out.getvalue()

        except Exception as e:
            self.logger.error("Audio trimming failed: %s", e)
            raise HTTPException(500, f"Audio trimming error: {e}") from e

    def transform(self, data: bytes, _path: str, etl_args: str) -> bytes:
        """
        ETL transform entrypoint.

        Args:
            data: Input audio bytes.
            _path: Ignored (path is not used here).
            etl_args: JSON string with trimming parameters.

        Returns:
            Trimmed audio bytes in requested format.
        """
        params = self._parse_etl_args(etl_args)
        start = float(params["from_time"])
        end = float(params["to_time"])
        fmt = params.get("audio_format", "wav")

        self.logger.debug(
            "Trimming audio from %.3f to %.3f seconds as %s", start, end, fmt
        )
        return self._trim_audio(data, start_time=start, end_time=end, fmt=fmt)


# Expose FastAPI app
fastapi_server = AudioSplitterServer()
fastapi_app = fastapi_server.app
