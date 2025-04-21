#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import json
import hashlib
import logging
from itertools import product

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl import ETLConfig

from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)
from tests.base import TestBase
from tests.const import MD5_TEMPLATE, SERVER_COMMANDS


logging.basicConfig(level=logging.INFO)


class TestMD5Transformer(TestBase):
    """Unit tests for AIStore MD5 ETL transformation."""

    def setUp(self):
        """Sets up test files and uploads them to the AIStore bucket."""
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

        for file in self.test_files.values():
            self.test_bck.object(file["filename"]).get_writer().put_file(file["source"])

    def md5_hash_file(self, filepath):
        """Computes the MD5 hash of a given file."""
        with open(filepath, "rb") as file:
            return hashlib.md5(file.read()).hexdigest()

    def compare_transformed_data_with_md5_hash(
        self, filename, original_filepath, etl_name
    ):
        """
        Fetches the transformed file and compares it against the expected MD5 hash.

        Args:
            filename (str): Name of the transformed file.
            original_filepath (str): Path to the original file.
            etl_name (str): Name of the ETL job.
        """
        transformed_data_bytes = (
            self.test_bck.object(filename)
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )
        original_file_hash = self.md5_hash_file(original_filepath)
        self.assertEqual(transformed_data_bytes.decode("utf-8"), original_file_hash)

    def run_md5_test(self, server_type, comm_type, arg_is_fqn):
        """
        Runs an MD5 transformation test using a specified communication type.

        Args:
            communication_type (str): The ETL communication type (HPULL, HPUSH).
        """
        etl_name = f"md5-{server_type}-{comm_type}-{generate_random_string(5)}"
        self.etls.append(etl_name)
        arg_type = "fqn" if arg_is_fqn else ""
        command = json.dumps(SERVER_COMMANDS[server_type])

        template = MD5_TEMPLATE.format(communication_type=comm_type, command=command)

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "md5")

        # Initialize ETL transformation
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=comm_type, arg_type=arg_type
        )

        # Validate MD5 hashes for all test files
        for file in self.test_files.values():
            self.compare_transformed_data_with_md5_hash(
                file["filename"], file["source"], etl_name
            )

    @cases(
        *product(
            ["flask", "fastapi", "http"],
            [ETL_COMM_HPULL, ETL_COMM_HPUSH],
            [True, False],
        )
    )
    def test_md5_transform(self, test_case):
        """Runs the MD5 ETL transformation for different communication types."""
        server_type, communication_type, arg_is_fqn = test_case

        logging.info(
            "Testing ETL with server: %s, communication: %s, FQN: %s",
            server_type,
            communication_type,
            arg_is_fqn,
        )
        self.run_md5_test(server_type, communication_type, arg_is_fqn)
