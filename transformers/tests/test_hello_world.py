#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import logging
from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import HELLO_WORLD

from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

FQN = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-hello-world
  annotations:
    communication_type: "hpull://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_hello_world:test
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: ["gunicorn", "main:app", "--workers", "20", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
      # command: ["uvicorn", "main:app", "--reload"]
      env:
        - name: ARG_TYPE
          value: "fqn"
      readinessProbe:
        httpGet:
          path: /health
          port: default
      volumeMounts:
        - name: ais
          mountPath: /tmp/
  volumes:
    - name: ais
      hostPath:
        path: /tmp/
        type: Directory
"""


class TestHelloWorldTransformer(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).put_file(self.test_text_source)

    def compare_transformed_data_with_hello_world(self, filename: str):
        transformed_data_bytes = (
            self.test_bck.object(filename).get(etl_name=self.test_etl.name).read_all()
        )
        self.assertEqual(b"Hello World!", transformed_data_bytes)

    def run_hello_world_test(self, communication_type: str, fqn_flag: bool = False):
        template = HELLO_WORLD.format(communication_type=communication_type)
        arg_type = "fqn" if fqn_flag else ""

        if fqn_flag:
            template = FQN

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "hello_world")

        self.test_etl.init_spec(
            template=template, communication_type=communication_type, arg_type=arg_type
        )

        logger.info(self.test_etl.view())

        self.compare_transformed_data_with_hello_world(self.test_image_filename)
        self.compare_transformed_data_with_hello_world(self.test_text_filename)

    def test_hello_world_hpull(self):
        self.run_hello_world_test(ETL_COMM_HPULL)

    def test_hello_world_hpush(self):
        self.run_hello_world_test(ETL_COMM_HPUSH)

    def test_hello_world_hrev(self):
        self.run_hello_world_test(ETL_COMM_HREV)

    def test_hello_world_hpull_fqn(self):
        self.run_hello_world_test(ETL_COMM_HPULL, True)

    def test_hello_world_hpush_fqn(self):
        self.run_hello_world_test(ETL_COMM_HPUSH, True)
