#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import hashlib

from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import MD5

from tests.utils import git_test_mode_format_image_tag_test
from tests.base import TestBase


class TestMD5Transformer(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).put_file(self.test_text_source)

    def md5_hash_file(self, filepath):
        with open(filepath, "rb") as file:
            file_content = file.read()
            return hashlib.md5(file_content).hexdigest()

    def compare_transformed_data_with_md5_hash(self, filename, original_filepath):
        transformed_data_bytes = (
            self.test_bck.object(filename).get(etl_name=self.test_etl.name).read_all()
        )
        original_file_hash = self.md5_hash_file(original_filepath)
        self.assertEqual(transformed_data_bytes.decode("utf-8"), original_file_hash)

    def run_md5_test(self, communication_type):
        template = MD5.format(communication_type=communication_type)

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "md5")

        self.test_etl.init_spec(
            template=template, communication_type=communication_type
        )

        self.compare_transformed_data_with_md5_hash(
            self.test_image_filename, self.test_image_source
        )
        self.compare_transformed_data_with_md5_hash(
            self.test_text_filename, self.test_text_source
        )

    def test_md5_hpull(self):
        self.run_md5_test(ETL_COMM_HPULL)

    def test_md5_hpush(self):
        self.run_md5_test(ETL_COMM_HPUSH)

    def test_md5_hrev(self):
        self.run_md5_test(ETL_COMM_HREV)
