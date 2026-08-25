"""
Stress testing Face Detection Transformer for 1 Million objects across all communication types.

Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
from datetime import datetime

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH

from tests.base import TestBase
from tests.utils import (
    cases,
    generate_random_string,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TestFaceDetectionStress(TestBase):
    """Stress test for AIStore ETL Face Detection transformation on a large dataset."""

    def setUp(self):
        """Sets up the test environment by defining the source bucket for face detection."""
        super().setUp()
        self.images_bck = self.client.bucket(bck_name="stress-test-face-detection")

    @cases(
        (ETL_COMM_HPUSH, "hpush-fastapi", ""),
        (ETL_COMM_HPULL, "hpull-fastapi", ""),
        # pylint: disable-next=fixme
        # TODO: Re-enable FQN cases after FaceDetection supports path input.
    )
    def test_face_detection(self, test_case):
        """Stress test face detection ETL transformation using various communication types."""
        comm_type, test_suffix, arg_type = test_case
        test_name = f"test_face_detection_{test_suffix}"
        etl_name = f"face-detect-{generate_random_string(5)}-{test_suffix}"
        self.etls.append(etl_name)

        self.initialize_etl(comm_type, etl_name, arg_type)
        self.execute_etl_job(test_name, etl_name)

    def initialize_etl(self, comm_type: str, etl_name: str, arg_type: str):
        """Initializes the ETL transformation with the specified parameters."""
        tag = "test" if self.git_test_mode == "true" else "latest"
        image = f"aistorage/transformer_face_detection:{tag}"

        # Initialize ETL transformation
        self.client.etl(etl_name).init(
            image=image,
            comm_type=comm_type,
            direct_file_access=arg_type == "fqn",
            FORMAT="jpg",
        )

        logger.info(
            "Initialized ETL: %s\n%s", etl_name, self.client.etl(etl_name).view()
        )

    def execute_etl_job(self, test_name: str, etl_name: str):
        """Executes the ETL transformation job and validates results."""
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

        logger.info("Test: %s | Duration: %s", test_name, time_elapsed)

        # Log results to metrics file
        with open("metrics.txt", "a+", encoding="utf-8") as file:
            file.write(f"{test_name} {time_elapsed}\n")
