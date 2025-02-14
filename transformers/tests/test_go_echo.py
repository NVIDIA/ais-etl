#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

from tests.base import TestBase
from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL
from aistore.sdk.etl.etl_templates import GO_ECHO
from aistore.sdk.etl import ETLConfig


class TestGoEchoTransformer(TestBase):
    """Unit tests for AIStore ETL Go Echo transformation."""

    def setUp(self):
        """Sets up the test environment by uploading test image and text files."""
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

        # Upload test files
        for file in self.test_files.values():
            self.test_bck.object(file["filename"]).get_writer().put_file(file["source"])

    def initialize_etl(self, etl_name: str):
        """Initializes the ETL template for Go Echo Transformer."""
        template = GO_ECHO.format(communication_type=ETL_COMM_HPULL)

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "echo_go")

        self.client.etl(etl_name).init_spec(
            template=template, communication_type=ETL_COMM_HPULL
        )

    @cases("image", "text")
    def test_go_echo(self, file_type):
        """Tests Go Echo transformation for both image and text files."""
        etl_name = f"go-echo-{generate_random_string(5)}"
        self.etls.append(etl_name)

        self.initialize_etl(etl_name)

        file_info = self.test_files[file_type]
        transformed_bytes = (
            self.test_bck.object(file_info["filename"])
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )

        with open(file_info["source"], "rb") as file:
            original_content = file.read()

        # Decode text files before comparison
        if file_type == "text":
            self.assertEqual(
                transformed_bytes.decode("utf-8"), original_content.decode("utf-8")
            )
        else:
            self.assertEqual(transformed_bytes, original_content)
