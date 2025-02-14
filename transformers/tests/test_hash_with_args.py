#
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import xxhash
import random

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl import ETLConfig

from tests.utils import git_test_mode_format_image_tag_test
from tests.base import TestBase

HASH_WITH_ARGS_SPEC_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-hash-with-args
  annotations:
    # Values it can take ["hpull://","hrev://","hpush://"]
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
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_bck.object(self.test_image_filename).get_writer().put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).get_writer().put_file(self.test_text_source)

    def seeded_hash_file(self, filepath, seed):
        with open(filepath, "rb") as file:
            file_content = file.read()
            hasher = xxhash.xxh64(seed=seed)
            hasher.update(file_content)
            return hasher.hexdigest()

    def compare_transformed_data_with_seeded_hash(self, filename, original_filepath, seed):
        transformed_data_bytes = (
            self.test_bck.object(filename).get_reader(etl=ETLConfig(name=self.test_etl.name, args=str(seed))).read_all()
        )
        original_file_hash = self.seeded_hash_file(original_filepath, seed)
        self.assertEqual(transformed_data_bytes.decode("utf-8"), original_file_hash)

    def run_seeded_hash_test(self, communication_type):
        seed_default=random.randint(0, 1000)
        template = HASH_WITH_ARGS_SPEC_TEMPLATE.format(communication_type=communication_type, seed_default=seed_default)

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "hash_with_args")

        self.test_etl.init_spec(
            template=template, communication_type=communication_type
        )

        self.compare_transformed_data_with_seeded_hash(
            self.test_image_filename, self.test_image_source, seed_default
        )
        self.compare_transformed_data_with_seeded_hash(
            self.test_text_filename, self.test_text_source, seed_default
        )

    def test_seeded_hash_hpull(self):
        self.run_seeded_hash_test(ETL_COMM_HPULL)

    def test_seeded_hash_hpush(self):
        self.run_seeded_hash_test(ETL_COMM_HPUSH)

    def test_seeded_hash_hrev(self):
        self.run_seeded_hash_test(ETL_COMM_HREV)
