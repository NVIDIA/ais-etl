"""
Stress testing Hello World Transformer for 1 Million objects for all communication types

Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
"""

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring
import logging
from datetime import datetime
from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV

# from aistore.sdk.etl_templates import FACE_DETECTION_TRANSFORMER
from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# TODO: move var to aistore.sdk.etl_templates after merge
FACE_DETECTION_TRANSFORMER = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-face-detection
  annotations:
    communication_type: "{communication_type}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_face_detection:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command:  ["gunicorn", "main:app", "--workers", "20", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: FORMAT
          value: "{format}"
        - name: ARG_TYPE
          value: "{arg_type}"
      volumeMounts:
        - name: ais
          mountPath: /tmp/ais
  volumes:
    - name: ais
      hostPath:
        path: /tmp/ais
        type: Directory
"""


class TestFaceDetectionStress(TestBase):
    def setUp(self):
        super().setUp()
        # dont delete this bucket
        self.images_bck = self.client.bucket(bck_name="stress-test-face-detection")

    def test_face_detection_hpush_fastapi(self):
        self.run_test(ETL_COMM_HPUSH, "test_face_detection_hpush_fastapi")

    def test_face_detection_hpull_fastapi(self):
        self.run_test(ETL_COMM_HPULL, "test_face_detection_hpull_fastapi")

    def test_face_detection_hrev_fastapi(self):
        self.run_test(ETL_COMM_HREV, "test_face_detection_hrev_fastapi")

    def test_face_detection_hpull_fastapi_fqn(self):
        self.run_test(
            ETL_COMM_HPULL, "test_face_detection_hpull_fastapi_fqn", arg_type="fqn"
        )

    def test_face_detection_hpush_fastapi_fqn(self):
        self.run_test(
            ETL_COMM_HPUSH, "test_face_detection_hpush_fastapi_fqn", arg_type="fqn"
        )

    def run_test(self, comm_type: str, func_name: str, arg_type: str = ""):
        template = FACE_DETECTION_TRANSFORMER.format(
            communication_type=comm_type, format="jpg", arg_type=arg_type
        )
        template = git_test_mode_format_image_tag_test(template, "face_detection")

        self.test_etl.init_spec(
            template=template, communication_type=comm_type, arg_type=arg_type
        )
        logger.info(self.test_etl.view())
        start_time = datetime.now()
        job_id = self.images_bck.transform(
            etl_name=self.test_etl.name, timeout="5m", to_bck=self.test_bck
        )
        self.client.job(job_id).wait(timeout=600, verbose=False)
        time_elapsed = datetime.now() - start_time
        self.assertEqual(self.client.job(job_id).status().err, "")
        self.assertEqual(
            len(self.images_bck.list_all_objects()),
            len(self.test_bck.list_all_objects()),
        )

        logger.info("%s %s", func_name, time_elapsed)
        with open("metrics.txt", "a+", encoding="utf-8") as file:
            file.write(f"{func_name} {time_elapsed}\n")
