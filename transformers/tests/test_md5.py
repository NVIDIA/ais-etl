#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import hashlib
import logging
from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl import ETLConfig

from .utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)
from tests.base import TestBase


logging.basicConfig(level=logging.INFO)
MD5_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-md5
  annotations:
    # Values it can take ["hpull://","hrev://","hpush://"]
    communication_type: "{communication_type}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_md5:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command: ["python", "/code/md5_server.py"]
      readinessProbe:
        httpGet:
          path: /health
          port: default
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


class TestMD5Transformer(TestBase):
    """Unit tests for AIStore MD5 ETL transformation."""

    def setUp(self):
        """Sets up test files and uploads them to the AIStore bucket."""
        super().setUp()
        self.test_files = {
            "image": {
                "filename": "test-image.jpg",
                "source": "./resources/test-image.jpg",
            },
            "text": {
                "filename": "test-text.txt",
                "source": "./resources/test-text.txt",
            },
        }

        for file in self.test_files.values():
            self.test_bck.object(file["filename"]).get_writer().put_file(file["source"])

    def md5_hash_file(self, filepath):
        """Computes the MD5 hash of a given file."""
        with open(filepath, "rb") as file:
            return hashlib.md5(file.read()).hexdigest()

    def compare_transformed_data_with_md5_hash(
        self, filename, original_filepath, etl_name
    ):
        """
        Fetches the transformed file and compares it against the expected MD5 hash.

        Args:
            filename (str): Name of the transformed file.
            original_filepath (str): Path to the original file.
            etl_name (str): Name of the ETL job.
        """
        transformed_data_bytes = (
            self.test_bck.object(filename)
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )
        original_file_hash = self.md5_hash_file(original_filepath)
        self.assertEqual(transformed_data_bytes.decode("utf-8"), original_file_hash)

    def run_md5_test(self, communication_type, fqn):
        """
        Runs an MD5 transformation test using a specified communication type.

        Args:
            communication_type (str): The ETL communication type (HPULL, HPUSH).
        """
        etl_name = f"md5-transformer-{generate_random_string(5)}"
        self.etls.append(etl_name)
        arg_type = "fqn" if fqn else ""
        template = MD5_TEMPLATE.format(communication_type=communication_type)

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "md5")

        # Initialize ETL transformation
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type, arg_type=arg_type
        )

        # Validate MD5 hashes for all test files
        for file in self.test_files.values():
            self.compare_transformed_data_with_md5_hash(
                file["filename"], file["source"], etl_name
            )

    @cases(
        (ETL_COMM_HPULL, True),
        (ETL_COMM_HPUSH, True),
        (ETL_COMM_HPULL, False),
        (ETL_COMM_HPUSH, False),
    )
    def test_md5_transform(self, test_case):
        """Runs the MD5 ETL transformation for different communication types."""
        communication_type, fqn = test_case
        logging.info(
            "Running MD5 transformation test with communication type: %s, fqn: %s",
            communication_type,
            fqn,
        )
        self.run_md5_test(communication_type, fqn)
