#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import bz2
import gzip
import hashlib
import os
import unittest

from aistore.sdk.etl_const import ETL_COMM_HPULL
from aistore.sdk.etl_templates import COMPRESS

from test_base import TestBase
from utils import git_test_mode_format_image_tag_test

class TestCompressTransformer(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_image_gz_filename = "test-image.jpg.gz"
        self.test_image_gz_source = "./resources/test-image.jpg.gz"
        self.test_text_gz_filename = "test-text.txt.gz"
        self.test_text_gz_source = "./resources/test-text.txt.gz"
        self.test_image_bz2_filename = "test-image.jpg.bz2"
        self.test_image_bz2_source = "./resources/test-image.jpg.bz2"
        self.test_text_bz2_filename = "test-text.txt.bz2"
        self.test_text_bz2_source = "./resources/test-text.txt.bz2"
        self.test_text_bz2_filename = "test-text.txt.bz2"
        self.test_text_bz2_source = "./resources/test-text.txt.bz2"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).put_file(self.test_text_source)
        self.test_bck.object(self.test_image_gz_filename).put_file(self.test_image_gz_source)
        self.test_bck.object(self.test_text_gz_filename).put_file(self.test_text_gz_source)
        self.test_bck.object(self.test_image_bz2_filename).put_file(self.test_image_bz2_source)
        self.test_bck.object(self.test_text_bz2_filename).put_file(self.test_text_bz2_source)
    
    def tearDown(self):
        super().tearDown()

    @unittest.skipIf(os.getenv('COMPRESS_ENABLE', 'true') == 'false', "COMPRESS is disabled")
    def test_compress_gzip(self):
        template = COMPRESS.format(communication_type=ETL_COMM_HPULL, arg1="--mode", val1="compress", arg2="--compression", val2="gzip")

        if self.git_test_mode == 'true':
            template = git_test_mode_format_image_tag_test(template, "compress")

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        compressed_image = self.test_bck.object(self.test_image_filename).get(etl_name=self.test_etl.name).read_all()
        compressed_text = self.test_bck.object(self.test_text_filename).get(etl_name=self.test_etl.name).read_all()

        self.assertNotEqual(compressed_image, b"Data processing failed")
        self.assertNotEqual(compressed_text, b"Data processing failed")
        
        # Decompress the files
        decompressed_image = gzip.decompress(compressed_image)
        decompressed_text = gzip.decompress(compressed_text)

        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()

        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()

        self.assertEqual(decompressed_image, original_image_content)
        self.assertEqual(decompressed_text.decode('utf-8'), original_text_content)

        # Calculate the checksums
        original_image_checksum = hashlib.md5(original_image_content).hexdigest()
        decompressed_image_checksum = hashlib.md5(decompressed_image).hexdigest()
        original_text_checksum = hashlib.md5(original_text_content.encode('utf-8')).hexdigest()
        decompressed_text_checksum = hashlib.md5(decompressed_text).hexdigest()

        # Validate the checksums
        self.assertEqual(original_image_checksum, decompressed_image_checksum)
        self.assertEqual(original_text_checksum, decompressed_text_checksum)

    @unittest.skipIf(os.getenv('COMPRESS_ENABLE', 'true') == 'false', "COMPRESS is disabled")
    def test_compress_bz2(self):
        template = COMPRESS.format(communication_type=ETL_COMM_HPULL, arg1="--mode", val1="compress", arg2="--compression", val2="bz2")

        if self.git_test_mode == 'true':
            template = git_test_mode_format_image_tag_test(template, "compress")

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        compressed_image = self.test_bck.object(self.test_image_filename).get(etl_name=self.test_etl.name).read_all()
        compressed_text = self.test_bck.object(self.test_text_filename).get(etl_name=self.test_etl.name).read_all()

        self.assertNotEqual(compressed_image, b"Data processing failed")
        self.assertNotEqual(compressed_text, b"Data processing failed")

        # Decompress the files
        decompressed_image = bz2.decompress(compressed_image)
        decompressed_text = bz2.decompress(compressed_text)

        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()

        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()
        
        self.assertEqual(decompressed_image, original_image_content)
        self.assertEqual(decompressed_text.decode('utf-8'), original_text_content)

        # Calculate the checksums
        original_image_checksum = hashlib.md5(original_image_content).hexdigest()
        decompressed_image_checksum = hashlib.md5(decompressed_image).hexdigest()
        original_text_checksum = hashlib.md5(original_text_content.encode('utf-8')).hexdigest()
        decompressed_text_checksum = hashlib.md5(decompressed_text).hexdigest()

        # Validate the checksums
        self.assertEqual(original_image_checksum, decompressed_image_checksum)
        self.assertEqual(original_text_checksum, decompressed_text_checksum)

    @unittest.skipIf(os.getenv('COMPRESS_ENABLE', 'true') == 'false', "COMPRESS is disabled")
    def test_decompress_gzip(self):
        template = COMPRESS.format(communication_type=ETL_COMM_HPULL, arg1="--mode", val1="decompress", arg2="--compression", val2="gzip")

        if self.git_test_mode == 'true':
            template = git_test_mode_format_image_tag_test(template, "compress")

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        decompressed_image = self.test_bck.object(self.test_image_gz_filename).get(etl_name=self.test_etl.name).read_all()
        decompressed_text = self.test_bck.object(self.test_text_gz_filename).get(etl_name=self.test_etl.name).read_all()

        self.assertNotEqual(decompressed_image, b"Data processing failed")
        self.assertNotEqual(decompressed_text, b"Data processing failed")

        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()

        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()

        self.assertEqual(decompressed_image, original_image_content)
        self.assertEqual(decompressed_text.decode('utf-8'), original_text_content)

        # Calculate the checksums
        original_image_checksum = hashlib.md5(original_image_content).hexdigest()
        decompressed_image_checksum = hashlib.md5(decompressed_image).hexdigest()
        original_text_checksum = hashlib.md5(original_text_content.encode('utf-8')).hexdigest()
        decompressed_text_checksum = hashlib.md5(decompressed_text).hexdigest()

        # Validate the checksums
        self.assertEqual(original_image_checksum, decompressed_image_checksum)
        self.assertEqual(original_text_checksum, decompressed_text_checksum)

    @unittest.skipIf(os.getenv('COMPRESS_ENABLE', 'true') == 'false', "COMPRESS is disabled")
    def test_decompress_bz2(self):
        template = COMPRESS.format(communication_type=ETL_COMM_HPULL, arg1="--mode", val1="decompress", arg2="--compression", val2="bz2")

        if self.git_test_mode == 'true':
            template = git_test_mode_format_image_tag_test(template, "compress")

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        decompressed_image = self.test_bck.object(self.test_image_bz2_filename).get(etl_name=self.test_etl.name).read_all()
        decompressed_text = self.test_bck.object(self.test_text_bz2_filename).get(etl_name=self.test_etl.name).read_all()

        self.assertNotEqual(decompressed_image, b"Data processing failed")
        self.assertNotEqual(decompressed_text, b"Data processing failed")

        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()

        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()

        self.assertEqual(decompressed_image, original_image_content)
        self.assertEqual(decompressed_text.decode('utf-8'), original_text_content)

        # Calculate the checksums
        original_image_checksum = hashlib.md5(original_image_content).hexdigest()
        decompressed_image_checksum = hashlib.md5(decompressed_image).hexdigest()
        original_text_checksum = hashlib.md5(original_text_content.encode('utf-8')).hexdigest()
        decompressed_text_checksum = hashlib.md5(decompressed_text).hexdigest()

        # Validate the checksums
        self.assertEqual(original_image_checksum, decompressed_image_checksum)
        self.assertEqual(original_text_checksum, decompressed_text_checksum)
