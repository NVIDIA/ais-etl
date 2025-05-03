"""
Pytest suite for the HashWithArgs ETL transformer.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import random
import logging
from pathlib import Path
from typing import Dict

import pytest
import xxhash
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket

from tests.const import (
    INLINE_PARAM_COMBINATIONS,
    HASH_WITH_ARGS_TEMPLATE,
)

# Configure module-level logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def _upload_test_files(test_bck: Bucket, local_files: Dict[str, Path]) -> None:
    """
    Upload files to the specified bucket.
    """
    for filename, path in local_files.items():
        logger.debug("Uploading %s to bucket %s", filename, test_bck.name)
        test_bck.object(filename).get_writer().put_file(str(path))


def _calculate_hash(data, seed):
    """Computes the seeded hash of a given file."""
    hasher = xxhash.xxh64(seed=seed)
    hasher.update(data)
    return hasher.hexdigest().encode()


def _verify_test_files(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_name: str,
) -> None:
    """
    Verify that the files in the bucket match the hash.
    """
    for filename, path in local_files.items():
        seed = random.randint(0, 1000)
        reader = test_bck.object(filename).get_reader(
            etl=ETLConfig(etl_name, args=str(seed))
        )
        transformed = reader.read_all()
        original = Path(path).read_bytes()
        original_hash = _calculate_hash(original, seed)
        assert (
            transformed == original_hash
        ), f"Hash mismatch for {filename}: expected {original_hash}, got {transformed}"


# pylint: disable=too-many-arguments
@pytest.mark.parametrize("server_type, comm_type, use_fqn", INLINE_PARAM_COMBINATIONS)
def test_echo_transformer(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_factory,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    Validate the Python-based Hash With Args ETL transformer.
    Upload sample files, initialize the ETL, then assert hash.
    """
    # Upload inputs
    _upload_test_files(test_bck, local_files)

    # Build and initialize ETL
    etl_name = etl_factory(
        tag="hash-with-args",
        server_type=server_type,
        template=HASH_WITH_ARGS_TEMPLATE,
        communication_type=comm_type,
        use_fqn=use_fqn,
    )
    logger.info(
        "Initialized HashWithArgs ETL '%s' (server=%s, comm=%s, fqn=%s)",
        etl_name,
        server_type,
        comm_type,
        use_fqn,
    )

    _verify_test_files(
        test_bck,
        local_files,
        etl_name,
    )
