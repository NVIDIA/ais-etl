#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import bz2
import gzip
import json

from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import COMPRESS

from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test


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

    def _get_compression_algorithm(self, compress_options):
        if compress_options.get("compression") == "bz2":
            algorithm = bz2
        else:
            algorithm = gzip

        return algorithm

    def _compress_test_helper(self, communication_type, compress_options):
        algorithm = self._get_compression_algorithm(compress_options)
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.test_bck.object(self.test_text_filename).put_file(self.test_text_source)
        compress_options = json.dumps(compress_options)
        template = COMPRESS.format(
            communication_type=communication_type, compress_options=compress_options
        )

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "compress")

        self.test_etl.init_spec(
            template=template, communication_type=communication_type
        )

        etl_compressed_img = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )

        etl_compressed_txt = (
            self.test_bck.object(self.test_text_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )

        with open(self.test_image_source, "rb") as file:
            original_image_content = file.read()

        with open(self.test_text_source, "r", encoding="utf-8") as file:
            original_text_content = file.read()

        self.assertEqual(
            algorithm.decompress(etl_compressed_img), original_image_content
        )
        self.assertEqual(
            original_text_content,
            algorithm.decompress(etl_compressed_txt).decode("utf-8"),
        )

    def _decompress_test_helper(self, communication_type, compress_options):
        algorithm = self._get_compression_algorithm(compress_options)

        if algorithm == bz2:
            self.test_bck.object(self.test_image_bz2_filename).put_file(
                self.test_image_bz2_source
            )
            self.test_bck.object(self.test_text_bz2_filename).put_file(
                self.test_text_bz2_source
            )
            compress_options = json.dumps(compress_options)
            template = COMPRESS.format(
                communication_type=communication_type, compress_options=compress_options
            )

            if self.git_test_mode == "true":
                template = git_test_mode_format_image_tag_test(template, "compress")

            self.test_etl.init_spec(
                template=template, communication_type=communication_type
            )
            etl_decompressed_img = (
                self.test_bck.object(self.test_image_bz2_filename)
                .get(etl_name=self.test_etl.name)
                .read_all()
            )
            etl_decompressed_txt = (
                self.test_bck.object(self.test_text_bz2_filename)
                .get(etl_name=self.test_etl.name)
                .read_all()
                .decode("utf-8")
            )
        elif algorithm == gzip:
            self.test_bck.object(self.test_image_gz_filename).put_file(
                self.test_image_gz_source
            )
            self.test_bck.object(self.test_text_gz_filename).put_file(
                self.test_text_gz_source
            )
            compress_options = json.dumps(compress_options)
            template = COMPRESS.format(
                communication_type=communication_type, compress_options=compress_options
            )

            if self.git_test_mode == "true":
                template = git_test_mode_format_image_tag_test(template, "compress")

            self.test_etl.init_spec(
                template=template, communication_type=communication_type
            )
            etl_decompressed_img = (
                self.test_bck.object(self.test_image_gz_filename)
                .get(etl_name=self.test_etl.name)
                .read_all()
            )
            etl_decompressed_txt = (
                self.test_bck.object(self.test_text_gz_filename)
                .get(etl_name=self.test_etl.name)
                .read_all()
                .decode("utf-8")
            )
        else:
            raise ValueError("Unexpected compression algorithm")

        with open(self.test_image_source, "rb") as file:
            original_image_content = file.read()

        with open(self.test_text_source, "r", encoding="utf-8") as file:
            original_text_content = file.read()

        self.assertEqual(original_image_content, etl_decompressed_img)
        self.assertEqual(original_text_content, etl_decompressed_txt)

    def test_default_compress_hpull(self):
        self._compress_test_helper(ETL_COMM_HPULL, {})

    def test_default_compress_hpush(self):
        self._compress_test_helper(ETL_COMM_HPUSH, {})

    def test_default_compress_hrev(self):
        self._compress_test_helper(ETL_COMM_HREV, {})

    def test_gzip_compress_hpull(self):
        self._compress_test_helper(ETL_COMM_HPULL, {"compression": "gzip"})

    def test_gzip_compress_hpush(self):
        self._compress_test_helper(ETL_COMM_HPUSH, {"compression": "gzip"})

    def test_gzip_compress_hrev(self):
        self._compress_test_helper(ETL_COMM_HREV, {"compression": "gzip"})

    def test_bz2_compress_hpull(self):
        self._compress_test_helper(ETL_COMM_HPULL, {"compression": "bz2"})

    def test_bz2_compress_hpush(self):
        self._compress_test_helper(ETL_COMM_HPUSH, {"compression": "bz2"})

    def test_bz2_compress_hrev(self):
        self._compress_test_helper(ETL_COMM_HREV, {"compression": "bz2"})

    def test_gzip_decompress_hpull(self):
        self._decompress_test_helper(
            ETL_COMM_HPULL, {"mode": "decompress", "compression": "gzip"}
        )

    def test_gzip_decompress_hpush(self):
        self._decompress_test_helper(
            ETL_COMM_HPUSH, {"mode": "decompress", "compression": "gzip"}
        )

    def test_gzip_decompress_hrev(self):
        self._decompress_test_helper(
            ETL_COMM_HREV, {"mode": "decompress", "compression": "gzip"}
        )

    def test_bz2_decompress_hpull(self):
        self._decompress_test_helper(
            ETL_COMM_HPULL, {"mode": "decompress", "compression": "bz2"}
        )

    def test_bz2_decompress_hpush(self):
        self._decompress_test_helper(
            ETL_COMM_HPUSH, {"mode": "decompress", "compression": "bz2"}
        )

    def test_bz2_decompress_hrev(self):
        self._decompress_test_helper(
            ETL_COMM_HREV, {"mode": "decompress", "compression": "bz2"}
        )
