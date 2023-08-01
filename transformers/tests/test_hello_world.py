#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import os
import unittest

from tests.test_base import TestBase
from tests.utils import git_test_mode_format_image_tag_test

from aistore.sdk.etl_const import ETL_COMM_HPULL
from aistore.sdk.etl_templates import HELLO_WORLD


class TestHelloWorldTransformer(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).put_file(self.test_text_source)

    @unittest.skipIf(
        os.getenv("HELLO_WORLD_ENABLE", "true") == "false", "HELLO_WORLD is disabled"
    )
    def test_hello_world(self):
        template = HELLO_WORLD.format(communication_type=ETL_COMM_HPULL)

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "hello_world")

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

        # Compare file contents
        self.assertEqual(b"Hello World!", transformed_image_bytes)
        self.assertEqual(b"Hello World!", transformed_text_bytes)
