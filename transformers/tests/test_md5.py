"""
Pytest suite for the MD5 ETL transformer.

For each combination of server backend (Flask, FastAPI, HTTP),
communication mode (HPULL/HPUSH), and argument style (FQN vs relative), this test:
  1. Uploads sample image and text files into a fresh bucket.
  2. Creates an MD5 ETL job via `etl_factory`.
  3. Transforms each file and asserts the output matches the MD5 checksum.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
import hashlib
from pathlib import Path
from typing import Dict

import pytest
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket

from tests.const import MD5_TEMPLATE, INLINE_PARAM_COMBINATIONS

# Configure module‐level logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


# pylint: disable=too-many-arguments
@pytest.mark.parametrize("server_type, comm_type, use_fqn", INLINE_PARAM_COMBINATIONS)
def test_md5_transformer(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_factory,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    Validate the MD5 ETL transformer across runtimes and communication modes.

    Args:
        test_bck:    fresh bucket fixture
        local_files: mapping of filename -> Path for inputs
        etl_factory: factory fixture to create ETL jobs
        server_type: 'flask' | 'fastapi' | 'http'
        comm_type:   ETL_COMM_HPULL | ETL_COMM_HPUSH
        use_fqn:     whether to pass FQN or relative paths
    """
    # 1) Upload inputs
    for filename, path in local_files.items():
        logging.debug("Uploading %s to %s", filename, test_bck.name)
        test_bck.object(filename).get_writer().put_file(str(path))

    # 2) Initialize ETL
    etl_name = etl_factory(
        tag="md5",
        server_type=server_type,
        template=MD5_TEMPLATE,
        communication_type=comm_type,
        use_fqn=use_fqn,
    )
    logging.info(
        "Initialized MD5 ETL '%s' (server=%s, comm=%s, fqn=%s)",
        etl_name,
        server_type,
        comm_type,
        use_fqn,
    )

    # 3) Run transform and assert checksum
    for filename, path in local_files.items():
        # compute expected MD5 of original file
        expected = hashlib.md5(Path(path).read_bytes()).hexdigest().encode()

        # fetch transformed result
        result_bytes = (
            test_bck.object(filename).get_reader(etl=ETLConfig(etl_name)).read_all()
        )

        assert (
            result_bytes == expected
        ), f"ETL {etl_name} MD5 mismatch for {filename}: expected {expected!r}, got {result_bytes!r}"
