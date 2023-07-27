#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import hashlib
import os
import unittest

from aistore.sdk.etl_const import ETL_COMM_HPULL
from aistore.sdk.etl_templates import MD5

from test_base import TestBase
from utils import git_test_mode_format_image_tag_test

class TestMD5Transformer(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).put_file(self.test_text_source)
    
    def tearDown(self):
        super().tearDown()

    @unittest.skipIf(os.getenv('MD5_ENABLE', 'true') == 'false', "MD5 is disabled")
    def test_md5(self):
        template = MD5.format(communication_type=ETL_COMM_HPULL)

        if self.git_test_mode == 'true':
            template = git_test_mode_format_image_tag_test(template, "md5")

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        transformed_image_bytes = self.test_bck.object(self.test_image_filename).get(etl_name=self.test_etl.name).read_all()
        transformed_text_bytes = self.test_bck.object(self.test_text_filename).get(etl_name=self.test_etl.name).read_all()

        # Compare image content
        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()  
            md5 = hashlib.md5()
            md5.update(original_image_content)
            hash = md5.hexdigest()

        self.assertEqual(transformed_image_bytes.decode('utf-8'), hash)

        # Compare text content
        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()
            md5 = hashlib.md5()
            md5.update(original_text_content.encode('utf-8'))
            hash = md5.hexdigest()

        self.assertEqual(transformed_text_bytes.decode('utf-8'), hash)
