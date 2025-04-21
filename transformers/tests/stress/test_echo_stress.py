"""
Stress test for the Echo Transformer using different server types
and communication modes.
Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

from itertools import product
from typing import Tuple

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from tests.stress.base_stress import TestBaseStress
from tests.utils import (
    generate_random_string,
    cases,
)
from tests.const import ECHO_TEMPLATE


class TestEchoStress(TestBaseStress):
    """Stress test for the Echo transformer (verifies src == dst for sampled objects)."""

    def setUp(self) -> None:
        super().setUp()
        self.source_bck = self.client.bucket(self.BUCKET_NAME)

    @cases(
        *product(
            ["flask", "fastapi", "http"],
            [ETL_COMM_HPULL, ETL_COMM_HPUSH],
            [True, False],
        )
    )
    def test_echo_stress(self, test_case: Tuple[str, str, bool]) -> None:
        """
        Test the Echo transformer with different server types and communication modes.
        """
        server_type, comm_type, use_fqn = test_case
        etl_name = f"echo-{server_type}-{comm_type}-{generate_random_string(5)}"
        self.etls.append(etl_name)
        arg_type = "fqn" if use_fqn else ""
        label = f"ECHO | {server_type:<8} | {comm_type:<6} | {arg_type:<4}"
        self.logger.info("Starting %s (ETL=%s)", label, etl_name)

        # 1) Init ETL spec
        self._init_etl(
            etl_name, server_type, comm_type, arg_type, ECHO_TEMPLATE, "echo"
        )

        # 2) Run the transform job
        duration, samples = self._run_bck_transform_job(
            src_bck=self.source_bck,
            dst_bck=self.test_bck,
            etl_name=etl_name,
        )

        self.logger.info("%s completed in %s", label, duration)

        # 3) Verify that each sampled object was echoed back unchanged
        for name in samples:
            src_data = self.source_bck.object(name).get_reader().read_all()
            dst_data = self.test_bck.object(name).get_reader().read_all()
            self.assertEqual(
                src_data,
                dst_data,
                f"Content mismatch for object '{name}'",
            )

        # 4) Record metrics
        self.metrics.append((label, duration))
