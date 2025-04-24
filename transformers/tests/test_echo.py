"""
Pytest suite for the Echo and Go Echo ETL transformers.

This module runs two parameterized test functions:

1. `test_echo_transformer` covers the Python-based Echo transformer across:
   - server frameworks: Flask, FastAPI, HTTP
   - communication modes: hpull/hpush
   - argument styles: FQN vs ""

2. `test_go_echo_transformer` covers the Go-based Echo transformer for both image and text files.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
from pathlib import Path
from typing import Dict

import pytest
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket
from aistore.sdk.etl.etl_const import ETL_COMM_HPULL

from tests.const import (
    ECHO_TEMPLATE,
    ECHO_GO_TEMPLATE,
    INLINE_PARAM_COMBINATIONS,
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


def _verify_test_files(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_name: str,
) -> None:
    """
    Verify that the files in the bucket match the original files.
    """
    for filename, path in local_files.items():
        reader = test_bck.object(filename).get_reader(etl=ETLConfig(etl_name))
        output = reader.read_all()
        original = Path(path).read_bytes()
        assert (
            output == original
        ), f"ETL {etl_name} did not echo back {filename} correctly"


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
    Validate the Python-based Echo ETL transformer.
    Upload sample files, initialize the ETL, then assert round-trip equality.
    """
    # Upload inputs
    _upload_test_files(test_bck, local_files)

    # Build and initialize ETL
    etl_name = etl_factory(
        tag="echo",
        server_type=server_type,
        template=ECHO_TEMPLATE,
        communication_type=comm_type,
        use_fqn=use_fqn,
    )
    logger.info(
        "Initialized Echo ETL '%s' (server=%s, comm=%s, fqn=%s)",
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


# pylint: disable=fixme
# TODO: Implement HPUSH in Go Echo Transformer
# @pytest.mark.parametrize("comm_type", COMM_TYPES)
def test_go_echo_transformer(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_factory,
) -> None:
    """
    Validate the Go-based Echo ETL transformer for both image and text.
    """
    # Upload inputs
    _upload_test_files(test_bck, local_files)

    # Initialize Go Echo ETL
    etl_name = etl_factory(
        tag="echo-go",
        server_type="go-http",
        template=ECHO_GO_TEMPLATE,
        communication_type=ETL_COMM_HPULL,
        use_fqn=False,
    )

    # Execute transform and assert on each file
    _verify_test_files(
        test_bck,
        local_files,
        etl_name,
    )
