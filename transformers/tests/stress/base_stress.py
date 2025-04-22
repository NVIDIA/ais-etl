"""
Base class for transformer stress tests.
Initialized a bucket with 10,000 random 1MB objects in AIStore for offline transforms.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, List
import random
import json

from aistore.sdk import Client, Bucket, Object
from tests.base import TestBase
from tests.const import SERVER_COMMANDS
from tests.utils import format_image_tag_for_git_test_mode

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("TestBaseStress")


# pylint: disable=too-many-arguments, too-many-locals
class TestBaseStress(TestBase):
    """
    Base class for stress tests. It creates a bucket with a large number of objects.
    """

    bucket: Optional[Bucket] = None
    object: Optional[Object] = None
    metrics = []
    BUCKET_NAME = "stress-test-10000-objects"
    OBJECT_COUNT = 10000
    OBJECT_SIZE = 1024 * 1024  # 1MB
    NUM_THREADS = 32

    @classmethod
    def setUpClass(cls) -> None:
        cluster_endpoint = os.environ.get("AIS_ENDPOINT", "http://192.168.49.2:8080")
        cls.client = Client(cluster_endpoint, max_pool_size=50)
        cls.bucket = cls.client.bucket(cls.BUCKET_NAME)
        cls.bucket.create(exist_ok=True)
        cls.logger = logger

        existing_objects = set(obj.name for obj in cls.bucket.list_all_objects())
        if len(existing_objects) == cls.OBJECT_COUNT:
            cls.logger.info(
                "Bucket %s already contains %d objects. Skipping creation.",
                cls.BUCKET_NAME,
                cls.OBJECT_COUNT,
            )
            return

        cls.logger.info("Resetting bucket %s...", cls.BUCKET_NAME)
        cls.bucket.delete()
        cls.bucket.create(exist_ok=True)

        cls.logger.info(
            "Generating %d objects of size %d bytes each using %d threads.",
            cls.OBJECT_COUNT,
            cls.OBJECT_SIZE,
            cls.NUM_THREADS,
        )

        def upload(index):
            obj_name = f"object-{index:05d}.bin"
            cls.bucket.object(obj_name).get_writer().put_content(
                os.urandom(cls.OBJECT_SIZE)
            )
            return obj_name

        with ThreadPoolExecutor(max_workers=cls.NUM_THREADS) as executor:
            futures = {executor.submit(upload, i): i for i in range(cls.OBJECT_COUNT)}
            for i, future in enumerate(as_completed(futures)):
                future.result()
                if i % 100 == 0:
                    cls.logger.info("Uploaded %d/%d objects...", i, cls.OBJECT_COUNT)

        cls.logger.info(
            "Completed: Created %d objects in bucket '%s'.",
            cls.OBJECT_COUNT,
            cls.BUCKET_NAME,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if hasattr(cls, "metrics"):
            with open("metrics.txt", "a", encoding="utf-8") as f:
                for name, dur in sorted(cls.metrics, key=lambda x: x[1]):
                    line = f"{name:<40} {dur}"
                    cls.logger.info(line)  # Log to console
                    f.write(f"{line}\n")  # Write to file

    def _init_etl(
        self,
        etl_name: str,
        server_type: str,
        communication_type: str,
        arg_type: str,
        template_str: str,
        image_tag: str,
    ) -> None:
        """
        Register and initialize an ETL spec on the cluster.

        Args:
            etl_name (str): Unique name for this ETL job.
            server_type (str): Key into SERVER_COMMANDS for the server payload.
            communication_type (str): ETL_COMM_HPULL or ETL_COMM_HPUSH.
            arg_type (str): "fqn" or "" (full qualified name).
            template_str (str): The template string (e.g. ECHO_TEMPLATE or HELLO_WORLD).
            image_tag (str): Short tag used when formatting the image reference.
        """
        self.etls.append(etl_name)

        payload = json.dumps(SERVER_COMMANDS[server_type])
        rendered = template_str.format(
            communication_type=communication_type,
            command=payload,
        )
        rendered = format_image_tag_for_git_test_mode(rendered, image_tag)

        self.client.etl(etl_name).init_spec(
            template=rendered,
            communication_type=communication_type,
            arg_type=arg_type,
        )

    def _run_bck_transform_job(
        self,
        src_bck: Bucket,
        dst_bck: Bucket,
        etl_name: str,
        *,
        num_workers: int = 6,
        etl_timeout: str = "10m",
        wait_timeout: int = 600,
        sample_size: int = 5,
    ) -> Tuple[float, List[str]]:
        """
        Run an ETL transform job from src_bck to dst_bck and validate its success.

        Args:
            src_bck (Bucket): Source bucket.
            dst_bck (Bucket): Destination bucket.
            etl_name (str): Name of the ETL transformation.
            num_workers (int): Number of workers to use for the job.
            etl_timeout (str): Timeout for the transform call (e.g. "10m").
            wait_timeout (int): Seconds to wait for job completion.
            sample_size (int): How many random objects to verify and return.

        Returns:
            Tuple[float, List[str]]: (time_taken_seconds, list_of_sampled_object_names)
        """
        job_id = src_bck.transform(
            etl_name=etl_name,
            timeout=etl_timeout,
            to_bck=dst_bck,
            num_workers=num_workers,
        )
        job = self.client.job(job_id)

        # Wait for completion
        job.wait(timeout=wait_timeout, verbose=False)

        # Fetch metrics and status
        time_elapsed = job.get_total_time()
        status = job.status()
        self.assertEqual(
            status.err, "", f"ETL Job {job_id} failed with error: {status.err}"
        )

        # Verify all objects copied
        all_objs = dst_bck.list_all_objects()
        count = len(all_objs)
        self.assertEqual(
            self.OBJECT_COUNT,
            count,
            f"Object count mismatch: expected {self.OBJECT_COUNT}, got {count}",
        )

        # Pick a random sample to verify transformation
        names = [obj.name for obj in all_objs]
        sample_names = random.sample(names, min(sample_size, count))

        return time_elapsed, sample_names
