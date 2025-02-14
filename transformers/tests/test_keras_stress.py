"""
Stress testing Keras Transformer for 50K images across all communication types.

Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
from datetime import datetime
from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl.etl_templates import KERAS_TRANSFORMER

from tests.base import TestBase
from tests.utils import cases, generate_random_string

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TestKerasStress(TestBase):
    """Stress test for Keras Transformer with 50K images using different communication types."""

    def setUp(self):
        """Sets up the test environment by defining the source bucket for images."""
        super().setUp()
        self.images_bck = self.client.bucket(bck_name="stress-test-images")

    def run_test(self, comm_type: str, test_name: str, fqn_flag: bool = False):
        """
        Runs a Keras transformation stress test using AIStore ETL.

        Args:
            comm_type (str): ETL communication type (HPULL, HPUSH, HREV).
            test_name (str): Name of the test case for logging.
            fqn_flag (bool, optional): Whether to use fully qualified names (FQN). Defaults to False.
        """
        arg_type = "fqn" if fqn_flag else ""

        # Generate a unique ETL name
        etl_name = f"keras-transformer-{generate_random_string(5)}"
        self.etls.append(etl_name)

        # Generate the ETL template
        template = KERAS_TRANSFORMER.format(
            communication_type=comm_type,
            format="JPEG",
            transform='{"theta":40, "brightness":0.8, "zx":0.9, "zy":0.9}',
            arg_type=arg_type,
        )

        # Initialize ETL transformation
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=comm_type, arg_type=arg_type
        )

        logger.info(
            "Starting ETL test: %s (ETL: %s)\n%s",
            test_name,
            etl_name,
            self.client.etl(etl_name).view(),
        )

        start_time = datetime.now()

        # Start transformation job
        job_id = self.images_bck.transform(
            etl_name=etl_name,
            timeout="30m",
            to_bck=self.test_bck,
            ext={"JPEG": "JPEG"},
        )

        # Wait for the job to complete
        self.client.job(job_id).wait(timeout=1800)
        time_elapsed = datetime.now() - start_time

        # Check job status
        job_status = self.client.job(job_id).status()
        self.assertEqual(
            job_status.err, "", f"ETL Job {job_id} failed with error: {job_status.err}"
        )

        # Ensure all images were transformed correctly
        self.assertEqual(
            len(self.images_bck.list_all_objects()),
            len(self.test_bck.list_all_objects()),
            "Mismatch in number of transformed images.",
        )

        logger.info("Test: %s | Duration: %s", test_name, time_elapsed)

        # Log results to a metrics file
        with open("metrics.txt", "a+", encoding="utf-8") as file:
            file.write(f"{test_name} {time_elapsed}\n")

    @cases(
        (ETL_COMM_HPUSH, "test_keras_hpush_fastapi", False),
        (ETL_COMM_HPULL, "test_keras_hpull_fastapi", False),
        (ETL_COMM_HREV, "test_keras_hrev_fastapi", False),
        (ETL_COMM_HPULL, "test_keras_hpull_fastapi_fqn", True),
        (ETL_COMM_HPUSH, "test_keras_hpush_fastapi_fqn", True),
    )
    def test_keras_transformer(self, test_case):
        """Stress tests Keras ETL transformation using different communication types."""
        comm_type, test_name, fqn_flag = test_case
        self.run_test(comm_type, test_name, fqn_flag)
