"""
Pytest suite for the Compress ETL transformer.

Tests compression and decompression functionality with various compression types
and modes.

Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
"""

import gzip
import bz2
import logging
from pathlib import Path
from typing import Dict

import pytest
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket

from tests.const import (
    COMPRESS_TEMPLATE,
)

# FastAPI-only test parameters
FASTAPI_PARAM_COMBINATIONS = [
    ("fastapi", "hpull", True),
    ("fastapi", "hpull", False),
    ("fastapi", "hpush", True),
    ("fastapi", "hpush", False),
]

def _upload_test_files(test_bck: Bucket, local_files: Dict[str, Path]) -> None:
    """Upload files to the specified bucket."""
    for filename, path in local_files.items():
        test_bck.object(filename).get_writer().put_file(str(path))


def _verify_compression(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_name: str,
    compression_type: str = "gzip",
    mode: str = "compress",
) -> None:
    """
    Verify that the files in the bucket are correctly compressed/decompressed.
    """
    for filename, path in local_files.items():
        # Read original file
        original_data = Path(path).read_bytes()
        
        if mode == "decompress":
            # First compress the file using the specified compression type
            if compression_type == "gzip":
                compressed_data = gzip.compress(original_data)
            else:  # bz2
                compressed_data = bz2.compress(original_data)
            
            # Upload the compressed version
            writer = test_bck.object(filename).get_writer()
            writer.put_content(compressed_data)
        
        # Get transformed data
        etl_config = ETLConfig(
            etl_name,
            args={"mode": mode, "compression": compression_type}
        )
        
        reader = test_bck.object(filename).get_reader(etl=etl_config)
        transformed = reader.read_all()
        
        if mode == "compress":
            # Verify compression worked
            assert len(transformed) < len(original_data), \
                f"Compression did not reduce size for {filename}"
            
            # Verify we can decompress it
            if compression_type == "gzip":
                decompressed = gzip.decompress(transformed)
            else:  # bz2
                decompressed = bz2.decompress(transformed)
            
            assert decompressed == original_data, \
                f"Decompressed data doesn't match original for {filename}"
        else:  # decompress
            # Verify decompression worked
            assert transformed == original_data, \
                f"Decompressed data doesn't match original for {filename}"


@pytest.mark.parametrize("server_type, comm_type, use_fqn", FASTAPI_PARAM_COMBINATIONS)
@pytest.mark.parametrize("compression_type", ["gzip", "bz2"])
@pytest.mark.parametrize("mode", ["compress", "decompress"])
def test_compress_transformer(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_factory,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
    compression_type: str,
    mode: str,
) -> None:
    """
    Validate the Compress ETL transformer functionality.
    Tests both compression and decompression with different compression types.
    """
    # Upload inputs
    _upload_test_files(test_bck, local_files)

    # Build and initialize ETL
    etl_name = etl_factory(
        tag="compress",
        server_type=server_type,
        template=COMPRESS_TEMPLATE,
        communication_type=comm_type,
        use_fqn=use_fqn,
    )

    _verify_compression(
        test_bck,
        local_files,
        etl_name,
        compression_type,
        mode,
    )