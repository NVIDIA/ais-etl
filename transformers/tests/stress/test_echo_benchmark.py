"""
Test Echo Transformer Benchmark
This module contains a stress test for the Echo Transformer using different server types
and communication types.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

# pylint: disable=missing-class-docstring, missing-function-docstring, too-many-locals
import json
from itertools import product
import random

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH

from tests.stress.base_stress import TestBaseStress
from tests.utils import (
    format_image_tag_for_git_test_mode,
    generate_random_string,
    cases,
)
from tests.const import SERVER_COMMANDS, ECHO_TEMPLATE


class TestEchoStress(TestBaseStress):
    """Stress test for Echo Transformer using different communication types."""

    def setUp(self):
        """Sets up the test environment with a pre-existing source bucket."""
        super().setUp()
        self.source_bck = self.client.bucket(self.BUCKET_NAME)

    def run_echo_test(self, server_type, communication_type, arg_is_fqn):
        etl_name = (
            f"echo-{server_type}-{communication_type}-{generate_random_string(5)}"
        )
        self.etls.append(etl_name)

        command = json.dumps(SERVER_COMMANDS[server_type])
        template = ECHO_TEMPLATE.format(
            communication_type=communication_type, command=command
        )

        template = format_image_tag_for_git_test_mode(template, "echo")

        arg_type = "fqn" if arg_is_fqn else ""
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type, arg_type=arg_type
        )

        test_name = f"ECHO | {server_type:<8} | {communication_type:<6} | {arg_type:<4}"

        self.logger.info("Starting Echo ETL test: %s (ETL: %s)", test_name, etl_name)

        job_id = self.source_bck.transform(
            etl_name=etl_name, timeout="10m", to_bck=self.test_bck, num_workers=24
        )
        self.client.job(job_id).wait(timeout=600, verbose=False)

        time_elapsed = self.client.job(job_id).get_total_time()
        job_status = self.client.job(job_id).status()

        self.assertEqual(
            job_status.err, "", f"ETL Job {job_id} failed with error: {job_status.err}"
        )

        dst_objects = self.test_bck.list_all_objects()
        self.assertEqual(
            self.OBJECT_COUNT,
            len(dst_objects),
            f"Mismatch in object count: {self.OBJECT_COUNT} vs {len(dst_objects)}",
        )

        # Pick 5 random objects from the destination bucket
        random_objs = random.sample(dst_objects, 5)

        for obj_entry in random_objs:
            obj_name = obj_entry.name
            src_obj = self.source_bck.object(obj_name)
            dst_obj = self.test_bck.object(obj_name)

            src_content = src_obj.get_reader().read_all()
            dst_content = dst_obj.get_reader().read_all()

            self.assertEqual(
                src_content,
                dst_content,
                f"Content mismatch for object {obj_name}",
            )

        self.logger.info(
            "Test: %s | ETL: %s | Duration: %s", test_name, etl_name, time_elapsed
        )

        self.metrics.append((test_name, time_elapsed))

    @cases(
        *product(
            ["flask", "fastapi", "http"],
            [ETL_COMM_HPULL, ETL_COMM_HPUSH],
            [True, False],
        )
    )
    def test_echo_stress(self, test_case):
        self.logger.info("Running test case: %s", test_case)
        server_type, communication_type, arg_is_fqn = test_case
        self.run_echo_test(server_type, communication_type, arg_is_fqn)
