"""
Audio Manager ETL Server

This FastAPI server reads a newline-delimited JSON manifest from AIS, invokes an ETL
transformer for each record to slice audio files, and streams a TAR archive of the
resulting WAV segments — without buffering the entire archive in memory.

Environment variables:
- AIS_TARGET_URL (required): Base URL for AIS target, used for FQN or network fetch.
- AIS_ENDPOINT (required): AIS API endpoint for SDK client.
- SRC_BUCKET (required): Source bucket name containing input manifests and audio.
- SRC_PROVIDER: Optional bucket provider (default: "ais").
- OBJ_PREFIX: Optional prefix for input audio object keys.
- OBJ_EXTENSION: Audio file extension (default: "wav").
- ETL_NAME (required): Name of the ETL job to invoke.
- DIRECT_FROM_TARGET: Whether to use direct_put (default: "true").
- MAX_POOL_SIZE: HTTP connection pool size for AIS SDK client (default: "50").

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
"""

import io
import json
import os
import tarfile
from typing import Any, BinaryIO, Dict, Iterator, Optional

from aistore import Client
from aistore.sdk.etl import ETLConfig
from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class _StreamingTarBuffer:
    """Write-only buffer that lets you drain chunks as tarfile writes them."""

    def __init__(self) -> None:
        self._buf: io.BytesIO = io.BytesIO()

    def write(self, data: bytes) -> int:
        """Write data to the internal buffer."""
        self._buf.write(data)
        return len(data)

    def tell(self) -> int:
        """Return the current buffer position."""
        return self._buf.tell()

    def drain(self) -> bytes:
        """Return buffered data and reset."""
        val = self._buf.getvalue()
        self._buf = io.BytesIO()
        return val


class AudioManagerServer(FastAPIServer):  # pylint: disable=too-many-instance-attributes
    """
    Audio Manager Server for batch-splitting audio via ETL.

    Accepts newline-delimited JSON manifests (bytes) where each line is:
        {"id": "<object_id>", "part": <int>, "from_time": <float>, "to_time": <float>, ...}

    Returns:
        A streamed TAR archive of `<id>_<part>.wav` files produced by the ETL.
        Only one WAV file is held in memory at a time.
    """

    def __init__(self, port: int = 8000) -> None:
        super().__init__(port=port)
        # Load and validate configuration
        self.host_target = os.getenv("AIS_TARGET_URL") or self._fatal("AIS_TARGET_URL")
        self.ais_endpoint = os.getenv("AIS_ENDPOINT") or self._fatal("AIS_ENDPOINT")
        self.bucket_name = os.getenv("SRC_BUCKET") or self._fatal("SRC_BUCKET")
        self.provider = os.getenv("SRC_PROVIDER", "ais")
        self.prefix = os.getenv("OBJ_PREFIX", "")
        self.extension = os.getenv("OBJ_EXTENSION", "wav")
        self.etl_name = os.getenv("ETL_NAME") or self._fatal("ETL_NAME")
        self.direct_from_target = os.getenv("DIRECT_FROM_TARGET", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        self.max_pool_size = int(os.getenv("MAX_POOL_SIZE", "50"))

        # Initialize AIS SDK client and source bucket
        self.ais_client = Client(
            self.ais_endpoint, max_pool_size=self.max_pool_size, timeout=None
        )
        self.src_bucket = self.ais_client.bucket(
            bck_name=self.bucket_name, provider=self.provider
        )

        self.logger.info(
            "AudioManagerServer initialized for bucket %s", self.bucket_name
        )

    @staticmethod
    def _fatal(var: str) -> None:
        """Helper to raise on missing required environment variable."""
        raise ValueError(f"Environment variable '{var}' is required")

    def _process_json_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse and validate one JSON manifest line.

        Returns:
            A dict with required keys if valid, else None.
        """
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON: %s (%s)", line, e)
            return None

        required = {"id", "part", "from_time", "to_time"}
        if not required.issubset(record):
            self.logger.warning("Missing keys in JSON: %s", line)
            return None

        return record

    def _fetch_transformed_audio(self, record: Dict[str, Any]) -> bytes:
        """
        Invoke the ETL transformer for one audio slice.

        Args:
            record: Parsed JSON with "id", "part", "from_time", "to_time", etc.

        Returns:
            Raw bytes of the sliced WAV file.
        """
        obj_key = f"{self.prefix}{record['id']}.{self.extension}"
        self.logger.debug("Request ETL '%s' for %s", self.etl_name, obj_key)

        cfg = ETLConfig(name=self.etl_name, args=record)
        reader = self.src_bucket.object(obj_key).get_reader(
            etl=cfg, direct=self.direct_from_target
        )
        return reader.read_all()

    def transform_stream(
        self, reader: BinaryIO, _path: str, _etl_args: str
    ) -> Iterator[bytes]:
        """
        Stream a TAR archive of audio segments given a JSONL manifest.

        Uses tarfile streaming mode ('w|') and a drainable buffer so that
        only one WAV file is held in memory at a time. Each chunk is yielded
        as soon as tarfile writes it.

        Args:
            reader: File-like object containing JSONL manifest data.
            _path: Object path (unused).
            _etl_args: ETL arguments (unused).

        Yields:
            bytes: Chunks of the TAR archive.
        """
        data = reader.read()
        if isinstance(data, (bytes, bytearray)):
            data = data.decode()
        self.logger.info("transform_stream: received %d bytes", len(data))

        buf = _StreamingTarBuffer()
        processed, errors = 0, 0

        with tarfile.open(fileobj=buf, mode="w|", format=tarfile.GNU_FORMAT) as tar:
            for idx, line in enumerate(
                (l.strip() for l in data.splitlines() if l.strip()), start=1
            ):
                record = self._process_json_line(line)
                if record is None:
                    self.logger.warning("Skipping invalid manifest line %d", idx)
                    continue

                try:
                    self.logger.debug(
                        "Line %d: fetching audio for %s", idx, record["id"]
                    )
                    audio = self._fetch_transformed_audio(record)
                    tar_info = tarfile.TarInfo(
                        name=f"{record['id']}_{record['part']}.wav"
                    )
                    tar_info.size = len(audio)
                    tar.addfile(tarinfo=tar_info, fileobj=io.BytesIO(audio))
                    processed += 1

                    chunk = buf.drain()
                    if chunk:
                        self.logger.debug(
                            "Line %d: yielding %d bytes (total processed: %d)",
                            idx,
                            len(chunk),
                            processed,
                        )
                        yield chunk

                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors += 1
                    self.logger.error("Line %d failed: %s", idx, e)

        # Yield final TAR end-of-archive markers written by tar.close() (via with)
        chunk = buf.drain()
        if chunk:
            yield chunk

        self.logger.info(
            "transform_stream: done — processed=%d, errors=%d",
            processed,
            errors,
        )


# Expose FastAPI app
fastapi_server = AudioManagerServer()
fastapi_app = fastapi_server.app
