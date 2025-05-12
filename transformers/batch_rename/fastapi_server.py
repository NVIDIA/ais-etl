"""
A FastAPI-based ETL server that renames objects based on a regex pattern
and stores them to a destination bucket with a new prefix.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import re

from aistore import Client
from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class BatchRenameServer(FastAPIServer):
    """
    ETL server that renames input objects based on a pattern match.

    If the object path matches the regex pattern defined by FILE_PATTERN,
    the object is renamed by applying DST_PREFIX and written to DST_BUCKET.

    Environment Variables:
        FILE_PATTERN         - Regex pattern to match object paths (required)
        DST_PREFIX          - Prefix to apply to renamed objects (required)
        DST_BUCKET           - Destination bucket name (required)
        DST_BUCKET_PROVIDER  - Storage provider for the destination bucket (default: "ais")
        AIS_ENDPOINT         - AIStore endpoint URL (required)
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        super().__init__(host=host, port=port)
        self.pattern = os.getenv("FILE_PATTERN") or self._fatal("FILE_PATTERN")
        self.prefix = os.getenv("DST_PREFIX") or self._fatal("DST_PREFIX")
        self.dst_bucket = os.getenv("DST_BUCKET") or self._fatal("DST_BUCKET")
        self.ais_endpoint = os.getenv("AIS_ENDPOINT") or self._fatal("AIS_ENDPOINT")
        self.dst_provider = os.getenv("DST_BUCKET_PROVIDER", "ais")
        self.ais_client = Client(self.ais_endpoint, timeout=None)

    @staticmethod
    def _fatal(var: str) -> None:
        """Raise an error for missing required environment variables."""
        raise ValueError(f"Environment variable '{var}' is required")

    def transform(self, data: bytes, path: str, *_):
        """
        Rename and redirect matching input object to a new path in the destination bucket.

        Args:
            data (bytes): Object content.
            path (str): Original object path.

        Returns:
            bytes: The original object content (unmodified).
        """
        if re.search(self.pattern, path):
            new_path = f"{self.prefix}{os.path.basename(path)}"
            # TODO: Add directly to target option
            self.ais_client.bucket(self.dst_bucket, provider=self.dst_provider).object(
                new_path
            ).get_writer().put_content(data)
        return data


# Initialize the ETL server and expose the FastAPI application
fastapi_server = BatchRenameServer()
fastapi_server.logger.setLevel("DEBUG")
fastapi_app = fastapi_server.app
