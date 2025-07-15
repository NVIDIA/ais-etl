"""
Pytest suite for the Hello-World ETL transformer.

For each combination of server framework (Flask, FastAPI, HTTP), communication mode (hpull/hpush),
and argument style (FQN vs relative), this test:
  1. Uploads two sample files into a fresh bucket.
  2. Creates an ETL job via `etl_factory`.
  3. Transforms each file and asserts the output equals `b"Hello World!"`.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
from pathlib import Path

import pytest
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket, Client

from tests.const import INLINE_PARAM_COMBINATIONS

# Configure module-level logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


# pylint: disable=too-many-arguments
@pytest.mark.parametrize("server_type, comm_type, use_fqn", INLINE_PARAM_COMBINATIONS)
def test_hello_world_transformer(
    client: Client,
    test_bck: Bucket,
    local_files: dict[str, Path],
    etl_factory: callable,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    Transform local_files via the Hello-World ETL and verify output.

    Args:
        client: AIS cluster client (session-scoped fixture).
        test_bck: fresh bucket for this test (function-scoped).
        local_files: mapping filename -> local Path of sample inputs.
        etl_factory: fixture to create+cleanup ETL jobs.
        server_type: framework to use ('flask', 'fastapi', 'http').
        comm_type: ETL_COMM_HPULL or ETL_COMM_HPUSH.
        use_fqn: whether to pass objects by fully-qualified name.
    """
    # Upload sample files
    for filename, path in local_files.items():
        logger.debug("Uploading %s to bucket %s", filename, test_bck.name)
        test_bck.object(filename).get_writer().put_file(path)

    # Build and initialize ETL
    etl_name = etl_factory(
        tag="hello-world",
        server_type=server_type,
        comm_type=comm_type,
        arg_type="fqn" if use_fqn else "",
    )
    logger.info(
        "Initialized Hello-World ETL '%s' (server=%s, comm=%s, fqn=%s)",
        etl_name,
        server_type,
        comm_type,
        use_fqn,
    )

    # Verify ETL configuration matches what we requested
    etl_details = client.etl(etl_name).view()
    expected_arg_type = "fqn" if use_fqn else ""
    expected_communication = f"{comm_type}://"

    assert etl_details.init_msg.communication == expected_communication, (
        f"ETL {etl_name} has communication='{etl_details.init_msg.communication}', "
        f"expected '{expected_communication}'"
    )
    assert etl_details.init_msg.argument == expected_arg_type, (
        f"ETL {etl_name} has argument='{etl_details.init_msg.argument}', "
        f"expected '{expected_arg_type}'"
    )

    # Execute transform and assert on each file
    for filename in local_files:
        reader = test_bck.object(filename).get_reader(etl=ETLConfig(etl_name))
        output = reader.read_all()
        assert (
            output == b"Hello World!"
        ), f"ETL {etl_name} produced unexpected output for '{filename}': {output!r}"
