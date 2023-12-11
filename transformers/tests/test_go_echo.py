#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test

from aistore.sdk.etl_const import ETL_COMM_HPULL
from aistore.sdk.etl_templates import GO_ECHO


class TestGoEchoTransformer(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).put_file(self.test_text_source)

    def test_go_echo(self):
        template = GO_ECHO.format(communication_type=ETL_COMM_HPULL)

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "echo_go")

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        transformed_image_bytes = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )
        transformed_text_bytes = (
            self.test_bck.object(self.test_text_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )

        # Compare image content
        with open(self.test_image_source, "rb") as file:
            original_image_content = file.read()
        self.assertEqual(transformed_image_bytes, original_image_content)

        # Compare text content
        with open(self.test_text_source, "r", encoding="utf-8") as file:
            original_text_content = file.read()
        self.assertEqual(transformed_text_bytes.decode("utf-8"), original_text_content)
