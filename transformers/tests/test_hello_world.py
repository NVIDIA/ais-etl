#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import logging
import json
from itertools import product

from aistore.sdk.etl import ETLConfig
from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from .base import TestBase
from .utils import (
    generate_random_string,
    format_image_tag_for_git_test_mode,
    cases,
)
from .const import SERVER_COMMANDS, HELLO_WORLD

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TestHelloWorldTransformer(TestBase):
    """Unit tests for Hello World AIStore ETL Transformer."""

    def setUp(self):
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

    def _assert_transformed_hello_world(self, filename: str, etl_name: str):
        """Asserts that the transformed file contains 'Hello World!'"""
        data = self.test_bck.object(filename).get_reader(etl=ETLConfig(etl_name)).read_all()
        self.assertEqual(data, b"Hello World!", f"Unexpected output for {filename}")

    def _init_etl(self, etl_name, server_type, communication_type, arg_type):
        """Initializes the ETL spec based on provided parameters."""
        command = json.dumps(SERVER_COMMANDS[server_type])
        template = HELLO_WORLD.format(communication_type=communication_type, command=command)

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "hello_world")

        self.client.etl(etl_name).init_spec(
            template=template,
            communication_type=communication_type,
            arg_type=arg_type,
        )

        logger.info("Initialized ETL '%s':\n%s", etl_name, self.client.etl(etl_name).view())

    def run_hello_world_test(self, server_type, communication_type, arg_is_fqn):
        """Runs Hello World transformer test for the given parameters."""
        etl_name = f"hello-world-{server_type}-{generate_random_string(5)}"
        self.etls.append(etl_name)

        arg_type = "fqn" if arg_is_fqn else ""
        self._init_etl(etl_name, server_type, communication_type, arg_type)

        for file in self.test_files.values():
            self._assert_transformed_hello_world(file["filename"], etl_name)

    @cases(
        *product(
            ["flask", "fastapi", "http"],
            [ETL_COMM_HPULL, ETL_COMM_HPUSH],
            [True, False],
        )
    )
    def test_hello_world_transformer(self, test_case):
        """Validates the Hello World ETL transformer across servers and communication types."""
        server_type, communication_type, arg_is_fqn = test_case
        logger.info("Running test: server=%s, comm=%s, fqn=%s", server_type, communication_type, arg_is_fqn)
        self.run_hello_world_test(server_type, communication_type, arg_is_fqn)
