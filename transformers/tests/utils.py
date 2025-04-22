#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import os
import random
import string
import base64
import logging
import json
import yaml

from aistore import Client
from aistore.sdk.const import URL_PATH_ETL, HTTP_METHOD_GET


def generate_random_string(length: int = 5) -> str:
    """Generates a random lowercase string of the specified length."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def format_image_tag_for_git_test_mode(template: str, image_name: str) -> str:
    """
    Modifies the container image in the given YAML template to use a test-specific image tag.

    Args:
        template (str): YAML template as a string.
        image_name (str): Name of the image to be formatted.

    Returns:
        str: Updated YAML template as a string.
    """
    parsed_template = yaml.safe_load(template)
    parsed_template["spec"]["containers"][0][
        "image"
    ] = f"aistorage/transformer_{image_name}:test"
    return yaml.dump(parsed_template)


def cases(*args):
    """
    Decorator for running a test function with multiple test cases.

    Args:
        *args: Arguments to be passed to the test function.

    Returns:
        Function wrapper.
    """

    def decorator(func):
        def wrapper(self, *inner_args, **kwargs):
            for arg in args:
                with self.subTest(arg=arg):
                    func(self, arg, *inner_args, **kwargs)

        return wrapper

    return decorator


# pylint: disable=protected-access
def log_etl(client: Client, etl_name: str) -> None:
    """
    Fetches and saves the logs of a specified ETL job.
    """
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, f"{etl_name}.log")

    try:
        resp = client._request_client.request(
            HTTP_METHOD_GET,
            f"/{URL_PATH_ETL}/{etl_name}/logs",
            timeout=20,
        )
        entries = json.loads(resp.content.decode("utf-8"))

        with open(log_path, "w", encoding="utf-8") as f:
            for entry in entries:
                tid = entry.get("target_id", "unknown")
                b64 = entry.get("logs", "").strip()

                raw = base64.b64decode(b64)
                decoded = raw.decode("utf-8", errors="replace")

                f.write(f"Target ID: {tid}\n")
                f.write(decoded)
                if not decoded.endswith("\n"):
                    f.write("\n")
                f.write("\n")

    except Exception as e:
        logging.error(
            "Warning: failed to fetch or write logs for ETL '%s': %s", etl_name, e
        )
