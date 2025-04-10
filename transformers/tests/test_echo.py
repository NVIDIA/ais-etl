#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import logging

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl.etl_templates import ECHO
from aistore.sdk.etl import ETLConfig

from tests.base import TestBase
from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)

logging.basicConfig(level=logging.INFO)

ECHO_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-echo
  annotations:
    # Values it can take ["hpull://","hrev://","hpush://"]
    communication_type: "{communication_type}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_echo:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: ["python", "/code/echo_server.py"]
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


class TestEchoTransformer(TestBase):
    """Unit tests for AIStore ETL Echo transformer."""

    def setUp(self):
        """Sets up test files and initializes the test bucket."""
        super().setUp()
        self.files = {
            "image": {
                "filename": "test-image.jpg",
                "source": "./resources/test-image.jpg",
            },
            "text": {
                "filename": "test-text.txt",
                "source": "./resources/test-text.txt",
            },
        }

        # Upload test files
        for file in self.files.values():
            self.test_bck.object(file["filename"]).get_writer().put_file(file["source"])

    def initialize_template(
        self, communication_type: str, etl_name: str, arg_is_fqn: bool
    ):
        """Initializes the ETL template for a given communication type."""
        template = ECHO_TEMPLATE.format(communication_type=communication_type)

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "echo")

        arg_type = "fqn" if arg_is_fqn else ""

        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type, arg_type=arg_type
        )

    def compare_transformed_data(self, filename: str, source: str, etl_name: str):
        """Compares transformed data with the original source file."""
        transformed_bytes = (
            self.test_bck.object(filename)
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )

        with open(source, "rb") as file:
            original_content = file.read()

        self.assertEqual(transformed_bytes, original_content)

    @cases(
        (ETL_COMM_HPULL, True),
        (ETL_COMM_HPUSH, True),
        (ETL_COMM_HPULL, False),
        (ETL_COMM_HPUSH, False),
    )
    def test_echo(self, test_case):
        """Tests Echo transformer for all communication types."""
        communication_type, arg_is_fqn = test_case

        logging.info(
            "Testing ETL with communication type: %s and FQN: %s",
            communication_type,
            arg_is_fqn,
        )

        etl_name = f"test-etl-{generate_random_string(5)}"
        self.etls.append(etl_name)

        self.initialize_template(communication_type, etl_name, arg_is_fqn)

        for file in self.files.values():
            self.compare_transformed_data(file["filename"], file["source"], etl_name)
