"""
HashWithArgs ETL transformer (FastAPI)

FastAPI-based ETL server that computes an XXHash64 digest of each request's payload,
optionally seeded via the `etl_args` query parameter.

Environment:
  SEED_DEFAULT default integer seed if etl_args is missing or invalid (default: 0)

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import logging
from typing import Optional

import xxhash
from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class HashWithArgs(FastAPIServer):
    """
    ETL server that computes an XXHash64 digest of each payload.

    Supports an optional `etl_args` parameter (string) specifying the numeric seed.
    """

    def __init__(
        self,
        port: int = 8000,
        *,
        default_seed: Optional[int] = None,
    ) -> None:
        """
        Initialize the HashWithArgs server.

        Args:
            port: TCP port to listen on (default 8000).
            default_seed: fallback seed if ETL args absent/invalid.
                If None, reads `SEED_DEFAULT` env var (defaulting to 0).
        """
        super().__init__(port=port)
        self.logger.setLevel(logging.DEBUG)
        if default_seed:
            self.default_seed = default_seed
        else:
            try:
                self.default_seed = int(os.getenv("SEED_DEFAULT", "0"))
            except ValueError:
                self.logger.warning(
                    "Invalid SEED_DEFAULT='%s', falling back to 0",
                    os.getenv("SEED_DEFAULT"),
                )
                self.default_seed = 0

    def transform(
        self,
        data: bytes,
        _path: str,
        etl_args: str,
    ) -> bytes:
        """
        Compute the XXHash64 digest of the input data.

        Args:
            data: Raw request payload.
            path: Request path or object key (unused here).
            etl_args: optional seed passed via `?etl_args=<seed>`.

        Returns:
            The lowercase hexadecimal digest as ASCII-encoded bytes.
        """
        seed = self.default_seed
        if etl_args:
            try:
                seed = int(etl_args)
            except ValueError:
                self.logger.warning(
                    "Invalid etl_args seed=%r, using default_seed=%d",
                    etl_args,
                    self.default_seed,
                )
        hasher = xxhash.xxh64(seed=seed)
        hasher.update(data)
        # hexdigest() is str → encode to ASCII bytes
        return hasher.hexdigest().encode("ascii")


# instantiate and expose
fastapi_server = HashWithArgs()
fastapi_app = fastapi_server.app
