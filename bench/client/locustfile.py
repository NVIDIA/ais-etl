"""
Test client for all the webservers.

Steps to run:
$ pip install locust
$ locust

Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
"""

from locust import HttpUser, task


class MyTestUser(HttpUser):
    @task
    def test_put_request(self):
        self._perform_put_request()

    @task
    def test_get_request(self):
        self._perform_get_request()

    def _perform_put_request(self):
        url = "/"
        data = "test"
        self.client.put(url=url, data=data)

    def _perform_get_request(self):
        url = "/"
        self.client.get(url=url)
