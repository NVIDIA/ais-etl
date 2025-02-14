#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import random
import string
import yaml


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
