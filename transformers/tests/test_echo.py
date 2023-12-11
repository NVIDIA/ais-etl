#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import ECHO

from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test


class TestEchoTransformer(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).put_file(self.test_text_source)

    def initialize_template(self, communication_type: str):
        template = ECHO.format(communication_type=communication_type)

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "echo")

        self.test_etl.init_spec(
            template=template, communication_type=communication_type
        )

    def compare_transformed_data(self, filename: str, source: str):
        transformed_bytes = (
            self.test_bck.object(filename).get(etl_name=self.test_etl.name).read_all()
        )

        with open(source, "rb") as file:
            original_content = file.read()

        self.assertEqual(transformed_bytes, original_content)

    def test_echo_hpull(self):
        self.initialize_template(ETL_COMM_HPULL)
        self.compare_transformed_data(self.test_image_filename, self.test_image_source)
        self.compare_transformed_data(self.test_text_filename, self.test_text_source)

    def test_echo_hpush(self):
        self.initialize_template(ETL_COMM_HPUSH)
        self.compare_transformed_data(self.test_image_filename, self.test_image_source)
        self.compare_transformed_data(self.test_text_filename, self.test_text_source)

    def test_echo_hrev(self):
        self.initialize_template(ETL_COMM_HREV)
        self.compare_transformed_data(self.test_image_filename, self.test_image_source)
        self.compare_transformed_data(self.test_text_filename, self.test_text_source)
