"""
Compress ETL Transformer (FastAPI)

FastAPI-based ETL server that compresses/decompresses data using various algorithms.
Supports gzip and bz2 compression with configurable mode (compress/decompress).

Environment Variables:
    AIS_TARGET_URL      - AIStore target URL (required for hpull mode)
    COMPRESS_OPTIONS    - JSON string with compression options:
                         {"mode": "compress|decompress", "compression": "gzip|bz2"}
                         Default: {"mode": "compress", "compression": "gzip"}

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import bz2
import gzip
import json
import logging
import os
from typing import Optional
from urllib.parse import unquote_plus

from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer

class CompressServer(FastAPIServer):
    """
    FastAPI-based server for compression/decompression ETL transformation.
    
    Supports both gzip and bz2 compression algorithms in compress and decompress modes.
    Configuration is done via environment variables.
    """

    def __init__(
            self,
            host: str = "0.0.0.0",
            port: int = 8000
    ):
        """
        Initialize the CompressServer.
        
        Fetches configuration from environment variables:
        - AIS_TARGET_URL: Target URL for AIStore (required for hpull mode)
        - COMPRESS_OPTIONS: JSON string with mode and compression settings
        
        Args:
            host: Interface to bind on (default "0.0.0.0")
            port: TCP port to listen on (default 8000)
        """
        super().__init__(host=host, port=port)
        
        self._init_compression_options()
        
        self.logger.info(
            "Initialized CompressServer with mode='%s', compression='%s'",
            self.mode, self.compression
        )

    def _init_compression_options(self):
        """Parse and validate compression options from COMPRESS_OPTIONS environment variable."""
        compress_options_str = os.environ.get("COMPRESS_OPTIONS", "{}") 
        
        try:
            compress_options = json.loads(compress_options_str)
        except json.JSONDecodeError:
            compress_options = {}
        
        # Set mode with validation
        self.mode = compress_options.get("mode", "compress")
        if self.mode not in ["compress", "decompress"]:
            self.mode = "compress"
        
        self.compression = compress_options.get("compression", "gzip")
        if self.compression not in ["gzip", "bz2"]:
            self.compression = "gzip"

    def transform(self,
                  data: bytes,
                  _path,
                  etl_args: str
    ) -> bytes:
        """
        Transform (compress or decompress) the input data.
        
        Args:
            data: Input data as bytes
            _path: Path to the object (unused)
            etl_args: JSON string with compression options:
                     {"mode": "compress|decompress", "compression": "gzip|bz2"}
            
        Returns:
            Transformed data as bytes
            
        Raises:
            ValueError: If unsupported mode or compression algorithm is specified
            Exception: If compression/decompression fails
        """
        # Use default values from init
        mode = self.mode
        compression = self.compression
        
        # Override with etl_args if provided
        if etl_args:
            try:
                # URL decode the ETL args first
                decoded_args = unquote_plus(etl_args)
                args_dict = json.loads(decoded_args)
                
                # Override mode if provided in etl_args
                if "mode" in args_dict and args_dict["mode"] in ["compress", "decompress"]:
                    mode = args_dict["mode"]
                
                # Override compression if provided in etl_args
                if "compression" in args_dict and args_dict["compression"] in ["gzip", "bz2"]:
                    compression = args_dict["compression"]
                        
            except json.JSONDecodeError:
                pass
        
        try:
            result = None
            if mode == "compress":
                if compression == "gzip":
                    result = gzip.compress(data)
                elif compression == "bz2":
                    result = bz2.compress(data)
            elif mode == "decompress":
                if compression == "gzip":
                    if not data.startswith(b"\x1f\x8b"):
                        raise ValueError("Input data is not in gzip format")
                    result = gzip.decompress(data)
                elif compression == "bz2":
                    if not data.startswith(b"BZh"):
                        raise ValueError("Input data is not in bz2 format")
                    result = bz2.decompress(data)
            
            if result is None:
                raise ValueError(
                    f"Unsupported data processing mode ({mode}) "
                    f"or compression algorithm ({compression})"
                )
            
            return result
            
        except Exception:
            raise


# Create the server instance and expose the FastAPI app
fastapi_server = CompressServer()
fastapi_app = fastapi_server.app
