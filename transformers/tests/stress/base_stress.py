"""
Script to create a bucket with 10,000 random 1MB objects in AIStore (multi-threaded).

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from aistore.sdk import Client, Bucket, Object
from tests.base import TestBase

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("TestBaseStress")


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
            with open("metrics.txt", "w", encoding="utf-8") as f:
                for name, dur in sorted(cls.metrics, key=lambda x: x[1]):
                    line = f"{name:<40} {dur}"
                    cls.logger.info(line)  # Log to console
                    f.write(f"{line}\n")  # Write to file
