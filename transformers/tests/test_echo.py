#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import logging
from itertools import product
import json

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl import ETLConfig

from tests.base import TestBase
from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)

logging.basicConfig(level=logging.INFO)


SERVER_COMMANDS = {
    "flask": [
        "gunicorn",
        "flask_server:flask_app",
        "--bind",
        "0.0.0.0:8000",
        "--workers",
        "4",
        "--log-level",
        "debug",
    ],
    "fastapi": [
        "uvicorn",
        "fastapi_server:fastapi_app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--workers",
        "4",
    ],
    "http": ["python", "http_server.py"],
}

ECHO_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-echo
  annotations:
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
      command: {command}
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
        *product(
            ["flask", "fastapi", "http"],
            [ETL_COMM_HPULL, ETL_COMM_HPUSH],
            [True, False],
        )
    )
    def test_echo(self, test_case):
        server_type, communication_type, arg_is_fqn = test_case

        logging.info(test_case)

        logging.info(
            "Testing ETL with server: %s, communication: %s, FQN: %s",
            server_type,
            communication_type,
            arg_is_fqn,
        )

        etl_name = f"test-etl-{server_type}-{generate_random_string(5)}"
        self.etls.append(etl_name)

        command = json.dumps(SERVER_COMMANDS[server_type])
        template = ECHO_TEMPLATE.format(
            communication_type=communication_type, command=command
        )

        logging.info("Template: %s", template)

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "echo")

        arg_type = "fqn" if arg_is_fqn else ""

        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type, arg_type=arg_type
        )

        for file in self.files.values():
            self.compare_transformed_data(file["filename"], file["source"], etl_name)
