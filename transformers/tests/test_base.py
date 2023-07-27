#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import os
import unittest

from aistore import Client

from utils import generate_random_str

class TestBase(unittest.TestCase):
    def setUp(self):
        self.endpoint = os.environ.get("AIS_ENDPOINT", "http://192.168.49.2:8080")
        self.git_test_mode = os.getenv('GIT_TEST', 'False')
        self.client = Client(self.endpoint)
        self.test_bck = self.client.bucket("etl-test-bucket").create(exist_ok=True)
        self.test_etl = self.client.etl("test-etl-" + generate_random_str()) 

    def tearDown(self):
        self.test_bck.delete()
        self.test_etl.stop()
        self.test_etl.delete()
