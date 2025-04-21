"""
Stress test for the Hello World Transformer using different server types
and communication types.
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
from tests.const import HELLO_WORLD


class TestHelloWorldStress(TestBaseStress):
    """Stress test for the Hello World transformer (verifies fixed payload)."""

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
    def test_hello_world_stress(self, test_case: Tuple[str, str, bool]) -> None:
        """
        Test the Hello World transformer with different server types and communication modes.
        """
        server_type, comm_type, use_fqn = test_case

        # 1) Build and register a unique ETL name
        suffix = generate_random_string(5)
        etl_name = f"hello-world-{server_type}-{comm_type}-{suffix}"
        arg_type = "fqn" if use_fqn else ""
        label = f"HELLO WORLD | {server_type:<8} | {comm_type:<6} | {arg_type:<4}"
        self.logger.info("Starting %s (ETL=%s)", label, etl_name)

        # 2) Initialize the ETL spec
        self._init_etl(
            etl_name, server_type, comm_type, arg_type, HELLO_WORLD, "hello_world"
        )

        # 3) Run the transform job
        duration, samples = self._run_bck_transform_job(
            src_bck=self.source_bck,
            dst_bck=self.test_bck,
            etl_name=etl_name,
        )

        # 4) Verify each sampled object contains the exact payload
        for name in samples:
            data = self.test_bck.object(name).get_reader().read_all()
            self.assertEqual(
                b"Hello World!",
                data,
                f"Content mismatch for object '{name}'",
            )

        # 5) Record results
        self.logger.info("%s completed in %s", label, duration)
        self.metrics.append((label, duration))
