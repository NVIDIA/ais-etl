#
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import xxhash
import random

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl import ETLConfig

from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)
from tests.base import TestBase

HASH_WITH_ARGS_SPEC_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-hash-with-args
  annotations:
    # Values it can take ["hpull://","hpush://"]
    communication_type: "{communication_type}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_hash_with_args:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 80
      command: ['/code/server.py', '--listen', '0.0.0.0', '--port', '80']
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: SEED_DEFAULT
          value: "{seed_default}"
"""


class TestHashWithArgsTransformer(TestBase):
    """Unit tests for AIStore ETL Hash With Args transformation."""

    def setUp(self):
        """Sets up the test environment by uploading test image and text files."""
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

        # Upload test files
        for file in self.test_files.values():
            self.test_bck.object(file["filename"]).get_writer().put_file(file["source"])

    def seeded_hash_file(self, filepath, seed):
        """Computes the seeded hash of a given file."""
        with open(filepath, "rb") as file:
            file_content = file.read()
            hasher = xxhash.xxh64(seed=seed)
            hasher.update(file_content)
            return hasher.hexdigest()

    def compare_transformed_data_with_seeded_hash(
        self, filename, original_filepath, seed, etl_name, use_args=False
    ):
        """Compares transformed data against the expected seeded hash."""
        etl_conf = ETLConfig(name=etl_name)
        if use_args:
            seed = random.randint(0, 1000)
            etl_conf.args = str(seed)

        transformed_data_bytes = (
            self.test_bck.object(filename).get_reader(etl=etl_conf).read_all()
        )
        original_file_hash = self.seeded_hash_file(original_filepath, seed)
        self.assertEqual(transformed_data_bytes.decode("utf-8"), original_file_hash)

    def run_seeded_hash_test(self, communication_type, use_args=False):
        """Executes a seeded hash test for a given communication type."""
        seed_default = random.randint(0, 1000)
        etl_name = f"hash-with-args-{generate_random_string(5)}"
        self.etls.append(etl_name)

        template = HASH_WITH_ARGS_SPEC_TEMPLATE.format(
            communication_type=communication_type, seed_default=seed_default
        )

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "hash_with_args")

        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type
        )

        for file_info in self.test_files.values():
            self.compare_transformed_data_with_seeded_hash(
                file_info["filename"],
                file_info["source"],
                seed_default,
                etl_name,
                use_args,
            )

    @cases(ETL_COMM_HPULL, ETL_COMM_HPUSH)
    def test_seeded_hash(self, communication_type):
        """Tests seeded hash transformation for different ETL communication types."""
        self.run_seeded_hash_test(communication_type, use_args=False)
        self.run_seeded_hash_test(communication_type, use_args=True)
