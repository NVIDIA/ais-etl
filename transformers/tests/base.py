#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import os
import unittest
from tests.utils import generate_random_str

from aistore import Client


class TestBase(unittest.TestCase):
    def setUp(self):
        self.endpoint = os.environ.get("AIS_ENDPOINT", "http://192.168.49.2:8080")
        self.git_test_mode = os.getenv("GIT_TEST", "false")
        self.client = Client(self.endpoint)
        self.test_bck = self.client.bucket(
            "test-bucket" + generate_random_str()
        ).create(exist_ok=True)
        self.test_etl = self.client.etl("test-etl-" + generate_random_str())

    def tearDown(self):
        self.test_bck.delete()
        self.test_etl.stop()
        self.test_etl.delete()
