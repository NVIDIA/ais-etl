"""
Stress testing Hello World Transformer for 1 Million objects across all communication types.

Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
from datetime import datetime

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl.etl_templates import HELLO_WORLD

from tests.base import TestBase
from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TestHelloWorldStress(TestBase):
    """Stress test for Hello World Transformer with 1 million objects using different communication types."""

    def setUp(self):
        """Sets up the test environment by defining the source bucket for transformation."""
        super().setUp()
        self.images_bck = self.client.bucket(bck_name="stress-test-objects")

    def run_test(self, comm_type: str, test_name: str, arg_type: str = ""):
        """
        Runs a Hello World transformation stress test using AIStore ETL.

        Args:
            comm_type (str): ETL communication type (HPULL, HPUSH, HREV).
            test_name (str): Name of the test case for logging.
            arg_type (str, optional): Whether to use fully qualified names (FQN). Defaults to "".
        """
        # Generate a unique ETL name
        etl_name = f"hello-world-{generate_random_string(5)}"
        self.etls.append(etl_name)

        # Generate the ETL template
        template = HELLO_WORLD.format(communication_type=comm_type, arg_type=arg_type)

        # Adjust template for Git test mode
        template = format_image_tag_for_git_test_mode(template, "hello_world")

        # Initialize ETL transformation
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=comm_type, arg_type=arg_type
        )

        logger.info(
            f"Starting ETL test: {test_name} (ETL: {etl_name})\n{self.client.etl(etl_name).view()}"
        )

        # Measure execution time
        start_time = datetime.now()

        # Start the transformation job
        job_id = self.images_bck.transform(
            etl_name=etl_name, timeout="5m", to_bck=self.test_bck
        )

        # Wait for job completion
        self.client.job(job_id).wait(timeout=600, verbose=False)

        # Calculate time taken
        time_elapsed = datetime.now() - start_time

        # Verify job status
        job_status = self.client.job(job_id).status()
        self.assertEqual(
            job_status.err, "", f"ETL Job {job_id} failed with error: {job_status.err}"
        )

        # Ensure object count matches between source and destination
        src_objects = len(self.images_bck.list_all_objects())
        dest_objects = len(self.test_bck.list_all_objects())
        self.assertEqual(
            src_objects,
            dest_objects,
            f"Mismatch in object count: {src_objects} vs {dest_objects}",
        )

        logger.info(
            "Test: %s | ETL: %s | Duration: %s", test_name, etl_name, time_elapsed
        )

        # Log results to metrics file
        with open("metrics.txt", "a+", encoding="utf-8") as file:
            file.write(f"{test_name} {time_elapsed}\n")

    @cases(
        (ETL_COMM_HPUSH, "test_hello_world_hpush_fastapi", ""),
        (ETL_COMM_HPULL, "test_hello_world_hpull_fastapi", ""),
        (ETL_COMM_HREV, "test_hello_world_hrev_fastapi", ""),
        (ETL_COMM_HPULL, "test_hello_world_hpull_fastapi_fqn", "fqn"),
        (ETL_COMM_HPUSH, "test_hello_world_hpush_fastapi_fqn", "fqn"),
    )
    def test_hello_world_stress(self, test_case):
        """Runs stress tests for Hello World ETL transformation with different communication types."""
        comm_type, test_name, arg_type = test_case
        self.run_test(comm_type, test_name, arg_type)
