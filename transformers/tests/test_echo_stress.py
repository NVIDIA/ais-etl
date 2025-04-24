"""
Pytest-based stress suite for the Echo ETL transformer.

This module:
  - Uses a pre-populated `stress_bucket` with 10,000 objects (session-scoped fixture).
  - Creates a fresh `test_bck` destination bucket per test.
  - Runs the Echo ETL across all server/comm/FQN combinations.
  - Verifies object counts and payload correctness on a random sample.
  - Records per-test durations into `metrics.txt`.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import random
import logging

import pytest
from aistore.sdk import Bucket

from tests.const import PARAM_COMBINATIONS, ECHO_TEMPLATE, LABEL_FMT

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


# pylint: disable=too-many-arguments, too-many-locals
@pytest.mark.stress
@pytest.mark.parametrize(
    "server_type, comm_type, use_fqn, direct_put", PARAM_COMBINATIONS
)
def test_echo_stress(
    stress_client,
    stress_bucket: Bucket,
    test_bck: Bucket,
    etl_factory,
    stress_metrics,
    stress_object_count,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
    direct_put: str,
):
    """
    Stress test for Echo ETL: copy 10k objects with transformation.
    """
    # 1) Initialize ETL
    label = LABEL_FMT.format(
        name="ECHO",
        server=server_type,
        comm=comm_type,
        arg="fqn" if use_fqn else "",
        direct=direct_put,
    )

    etl_name = etl_factory(
        tag="echo",
        server_type=server_type,
        template=ECHO_TEMPLATE,
        communication_type=comm_type,
        use_fqn=use_fqn,
        direct_put=direct_put,
    )

    # 2) Run transform job
    job_id = stress_bucket.transform(
        etl_name=etl_name,
        to_bck=test_bck,
        num_workers=24,
        timeout="10m",
    )
    job = stress_client.job(job_id)
    job.wait(timeout=600)
    duration = job.get_total_time()

    logger.info(
        "ETL '%s' completed in %ss (srv=%s, comm=%s, fqn=%s)",
        etl_name,
        duration,
        server_type,
        comm_type,
        use_fqn,
    )

    # 3) Verify counts
    objs = list(test_bck.list_all_objects())
    assert (
        len(objs) == stress_object_count
    ), f"Expected {stress_object_count} objects, got {len(objs)}"

    # 4) Sample and verify payload
    samples = random.sample(objs, 10)
    for entry in samples:
        data = test_bck.object(entry.name).get_reader().read_all()
        actual = stress_bucket.object(entry.name).get_reader().read_all()

        assert data == actual, f"Echo'd object didn't match for {entry.name}"

    # 5) Record metric
    stress_metrics.append((label, duration))
