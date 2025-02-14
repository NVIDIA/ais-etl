#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import logging
from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl.etl_templates import HELLO_WORLD
from aistore.sdk.etl import ETLConfig

from tests.base import TestBase
from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TestHelloWorldTransformer(TestBase):
    """Unit tests for the Hello World AIStore ETL Transformer."""

    def setUp(self):
        """Sets up the test environment by uploading test files to the bucket."""
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

    def compare_transformed_data_with_hello_world(self, filename: str, etl_name: str):
        """
        Fetches the transformed file and asserts that the output is "Hello World!".

        Args:
            filename (str): Name of the file to fetch and verify.
            etl_name (str): The ETL instance name.
        """
        transformed_data_bytes = (
            self.test_bck.object(filename)
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )
        self.assertEqual(
            b"Hello World!",
            transformed_data_bytes,
            f"File contents after transformation differ for {filename}",
        )

    def run_hello_world_test(self, communication_type: str, arg_type: str = ""):
        """
        Runs the Hello World ETL test for a given communication type.

        Args:
            communication_type (str): The ETL communication type (HPULL, HPUSH, HREV).
            arg_type (str, optional): Argument type ("fqn" for fully qualified names). Defaults to "".
        """
        # Generate a unique ETL name
        etl_name = f"hello-world-{generate_random_string(5)}"
        self.etls.append(etl_name)

        # Format the ETL template
        template = HELLO_WORLD.format(
            communication_type=communication_type, arg_type=arg_type
        )

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "hello_world")

        # Initialize ETL transformation
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type, arg_type=arg_type
        )

        logger.info(
            "ETL Spec for %s (ETL: %s):\n%s",
            communication_type,
            etl_name,
            self.client.etl(etl_name).view(),
        )

        # Compare the transformed output with "Hello World!"
        for file in self.test_files.values():
            self.compare_transformed_data_with_hello_world(file["filename"], etl_name)

    @cases(
        (ETL_COMM_HPULL, ""),
        (ETL_COMM_HPUSH, ""),
        (ETL_COMM_HREV, ""),
        (ETL_COMM_HPULL, "fqn"),
        (ETL_COMM_HPUSH, "fqn"),
    )
    def test_hello_world_transformer(self, test_case):
        """Tests Hello World ETL transformation with different communication types and argument types."""
        communication_type, arg_type = test_case
        self.run_hello_world_test(communication_type, arg_type)
