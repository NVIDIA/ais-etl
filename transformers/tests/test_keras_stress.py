"""
Stress testing Keras Transformer for 50k images for all communication types

Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
"""
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import logging
from datetime import datetime
from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import KERAS_TRANSFORMER
from tests.base import TestBase

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TestKerasStress(TestBase):
    def setUp(self):
        super().setUp()
        # Keep this bucket
        self.images_bck = self.client.bucket(bck_name="stress-test-images")

    def run_test(self, comm_type: str, func_name: str, fqn_flag: bool = False):
        arg_type = "fqn" if fqn_flag else ""
        template = KERAS_TRANSFORMER.format(
            communication_type=comm_type,
            format="JPEG",
            transform='{"theta":40, "brightness":0.8, "zx":0.9, "zy":0.9}',
            arg_type=arg_type,
        )
        self.test_etl.init_spec(
            template=template, communication_type=comm_type, arg_type=arg_type
        )

        start_time = datetime.now()
        job_id = self.images_bck.transform(
            etl_name=self.test_etl.name,
            timeout="30m",
            to_bck=self.test_bck,
            ext={"JPEG": "JPEG"},
        )
        self.client.job(job_id).wait(timeout=1800)
        time_elapsed = datetime.now() - start_time

        job_status = self.client.job(job_id).status()
        self.assertEqual(job_status.err, "")
        self.assertEqual(
            len(self.images_bck.list_all_objects()),
            len(self.test_bck.list_all_objects()),
        )

        logger.info("%s %s", func_name, time_elapsed)
        with open("metrics.txt", "a+", encoding="utf-8") as file:
            file.write(f"{func_name} {time_elapsed}\n")

    def test_keras_hpush_fastapi(self):
        self.run_test(ETL_COMM_HPUSH, "test_keras_hpush_fastapi")

    def test_keras_hpull_fastapi(self):
        self.run_test(ETL_COMM_HPULL, "test_keras_hpull_fastapi")

    def test_keras_hrev_fastapi(self):
        self.run_test(ETL_COMM_HREV, "test_keras_hrev_fastapi")

    def test_keras_hpull_fastapi_fqn(self):
        self.run_test(ETL_COMM_HPULL, "test_keras_hpull_fastapi_fqn", True)

    def test_keras_hpush_fastapi_fqn(self):
        self.run_test(ETL_COMM_HPUSH, "test_keras_hpush_fastapi_fqn", True)
