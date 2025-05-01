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
from itertools import product

from tests.const import (
    PARAM_COMBINATIONS,
    ECHO_TEMPLATE,
    ECHO_GO_TEMPLATE,
    LABEL_FMT,
    ETL_COMM_HPULL,
    ETL_COMM_HPUSH,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def _assert_objects_count_and_content(
    test_bck: Bucket, stress_bucket: Bucket, stress_object_count: int
):
    """
    Assert that the object count in the test bucket matches the expected count.
    """
    test_bck_summary = test_bck.summary()
    stress_bucket_summary = stress_bucket.summary()

    assert (
        test_bck_summary["ObjCount"] == stress_bucket_summary["ObjCount"]
    ), f"Expected {stress_bucket_summary['ObjCount']} objects, got {test_bck_summary['ObjCount']}"

    assert (
        test_bck_summary["ObjSize"] == stress_bucket_summary["ObjSize"]
    ), f"Expected {stress_bucket_summary['ObjSize']} object size, got {test_bck_summary['ObjSize']}"

    assert (
        test_bck_summary["TotalSize"]["size_all_present_objs"]
        == stress_bucket_summary["TotalSize"]["size_all_present_objs"]
    ), f"Expected {stress_bucket_summary['TotalSize']['size_all_present_objs']} total object size, got {test_bck_summary['TotalSize']['size_all_present_objs']}"

    objs = list(test_bck.list_all_objects())
    assert (
        len(objs) == stress_object_count
    ), f"Expected {stress_object_count} objects, got {len(objs)}"

    # Sample and verify payload
    samples = random.sample(objs, 10)
    for entry in samples:
        data = test_bck.object(entry.name).get_reader().read_all()
        actual = stress_bucket.object(entry.name).get_reader().read_all()

        assert data == actual, f"Echo'd object didn't match for {entry.name}"


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
    job.wait(timeout=600, verbose=False)
    duration = job.get_total_time()

    logger.info(
        "ETL '%s' completed in %ss (srv=%s, comm=%s, fqn=%s)",
        etl_name,
        duration,
        server_type,
        comm_type,
        use_fqn,
    )

    # 3) Verify counts and content
    _assert_objects_count_and_content(test_bck, stress_bucket, stress_object_count)

    # 4) Record metric
    stress_metrics.append((label, duration))


# pylint: disable=too-many-arguments, too-many-locals
@pytest.mark.stress
@pytest.mark.parametrize(
    "comm_type, use_fqn, direct_put",
    product([ETL_COMM_HPUSH, ETL_COMM_HPULL], [True, False], ["true", "false"]),
)
def test_go_echo_stress(
    stress_client,
    stress_bucket: Bucket,
    test_bck: Bucket,
    etl_factory,
    stress_metrics,
    stress_object_count,
    comm_type: str,
    use_fqn: bool,
    direct_put: str,
):
    """
    Stress test for Echo ETL: copy 10k objects with transformation.
    """
    # 1) Initialize ETL
    label = LABEL_FMT.format(
        name="ECHO-GO",
        server="go-http",
        comm=comm_type,
        arg="fqn" if use_fqn else "",
        direct=direct_put,
    )

    etl_name = etl_factory(
        tag="echo-go",
        server_type="go-http",
        template=ECHO_GO_TEMPLATE,
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
    job.wait(timeout=600, verbose=False)
    duration = job.get_total_time()

    logger.info(
        "ETL '%s' completed in %ss (comm=%s, fqn=%s)",
        etl_name,
        duration,
        comm_type,
        use_fqn,
    )

    # 3) Verify counts and content
    _assert_objects_count_and_content(test_bck, stress_bucket, stress_object_count)

    # 4) Record metric
    stress_metrics.append((label, duration))
