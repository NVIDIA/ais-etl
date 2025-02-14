#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import bz2
import gzip
import json

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl.etl_templates import COMPRESS
from aistore.sdk.etl import ETLConfig

from .base import TestBase
from .utils import format_image_tag_for_git_test_mode, cases, generate_random_string


class TestCompressTransformer(TestBase):
    """Unit tests for AIStore ETL compression and decompression transformations."""

    def setUp(self):
        """Sets up test files and initializes test bucket."""
        super().setUp()
        self.files = {
            "image": {
                "filename": "test-image.jpg",
                "source": "./resources/test-image.jpg",
            },
            "text": {
                "filename": "test-text.txt",
                "source": "./resources/test-text.txt",
            },
        }

        self.compressed_files = {
            "gzip": {
                "image": {
                    "filename": "test-image.jpg.gz",
                    "source": "./resources/test-image.jpg.gz",
                },
                "text": {
                    "filename": "test-text.txt.gz",
                    "source": "./resources/test-text.txt.gz",
                },
            },
            "bz2": {
                "image": {
                    "filename": "test-image.jpg.bz2",
                    "source": "./resources/test-image.jpg.bz2",
                },
                "text": {
                    "filename": "test-text.txt.bz2",
                    "source": "./resources/test-text.txt.bz2",
                },
            },
        }

    def _get_compression_algorithm(self, compress_options):
        """Returns the appropriate compression algorithm based on options."""
        return bz2 if compress_options.get("compression") == "bz2" else gzip

    def _initialize_etl(self, communication_type, compress_options, etl_name):
        """Initializes the ETL transformation for compression or decompression."""
        template = COMPRESS.format(
            communication_type=communication_type,
            compress_options=json.dumps(compress_options),
        )

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "compress")

        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type
        )

    def _compress_test_helper(self, communication_type, compress_options, etl_name):
        """Tests ETL compression for images and text files."""
        algorithm = self._get_compression_algorithm(compress_options)

        # Upload original files
        for file in self.files.values():
            self.test_bck.object(file["filename"]).get_writer().put_file(file["source"])

        # Initialize ETL transformation
        self._initialize_etl(communication_type, compress_options, etl_name)

        # Validate compressed output
        for file in self.files.values():
            etl_compressed = (
                self.test_bck.object(file["filename"])
                .get_reader(etl=ETLConfig(etl_name))
                .read_all()
            )

            with open(file["source"], "rb") as f:
                original_content = f.read()

            if file["filename"].endswith(".txt"):
                self.assertEqual(
                    original_content.decode("utf-8"),
                    algorithm.decompress(etl_compressed).decode("utf-8"),
                )
            else:
                self.assertEqual(original_content, algorithm.decompress(etl_compressed))

    def _decompress_test_helper(self, communication_type, compress_options, etl_name):
        """Tests ETL decompression for images and text files."""
        algorithm = self._get_compression_algorithm(compress_options)
        compression_type = "bz2" if algorithm == bz2 else "gzip"

        # Upload pre-compressed files
        for file in self.compressed_files[compression_type].values():
            self.test_bck.object(file["filename"]).get_writer().put_file(file["source"])

        # Initialize ETL transformation
        self._initialize_etl(communication_type, compress_options, etl_name)

        # Validate decompressed output
        for file_key, file in self.compressed_files[compression_type].items():
            etl_decompressed = (
                self.test_bck.object(file["filename"])
                .get_reader(etl=ETLConfig(etl_name))
                .read_all()
            )

            with open(self.files[file_key]["source"], "rb") as f:
                original_content = f.read()

            if file["filename"].endswith(".txt"):
                self.assertEqual(
                    original_content.decode("utf-8"), etl_decompressed.decode("utf-8")
                )
            else:
                self.assertEqual(original_content, etl_decompressed)

    @cases(ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV)
    def test_default_compress(self, communication_type):
        """Tests default compression for all communication types."""
        etl_name = f"test-etl-{generate_random_string(5)}"
        self.etls.append(etl_name)

        self._compress_test_helper(communication_type, {}, etl_name)

    @cases(ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV)
    def test_gzip_compress(self, communication_type):
        """Tests Gzip compression for all communication types."""
        etl_name = f"test-etl-{generate_random_string(5)}"
        self.etls.append(etl_name)

        self._compress_test_helper(
            communication_type, {"compression": "gzip"}, etl_name
        )

    @cases(ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV)
    def test_bz2_compress(self, communication_type):
        """Tests BZ2 compression for all communication types."""
        etl_name = f"test-etl-{generate_random_string(5)}"
        self.etls.append(etl_name)

        self._compress_test_helper(communication_type, {"compression": "bz2"}, etl_name)

    @cases(ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV)
    def test_gzip_decompress(self, communication_type):
        """Tests Gzip decompression for all communication types."""
        etl_name = f"test-etl-{generate_random_string(5)}"
        self.etls.append(etl_name)

        self._decompress_test_helper(
            communication_type, {"mode": "decompress", "compression": "gzip"}, etl_name
        )

    @cases(ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV)
    def test_bz2_decompress(self, communication_type):
        """Tests BZ2 decompression for all communication types."""
        etl_name = f"test-etl-{generate_random_string(5)}"
        self.etls.append(etl_name)

        self._decompress_test_helper(
            communication_type, {"mode": "decompress", "compression": "bz2"}, etl_name
        )
