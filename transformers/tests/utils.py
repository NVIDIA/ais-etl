#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import random
import string
import yaml


def generate_random_str():
    return "".join(random.choice(string.ascii_lowercase) for i in range(5))


def git_test_mode_format_image_tag_test(template, img):
    template = yaml.safe_load(template)
    template["spec"]["containers"][0]["image"] = f"aistorage/transformer_{img}:test"
    return yaml.dump(template)
