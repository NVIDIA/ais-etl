#!/usr/bin/env python
#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring, broad-exception-caught

import os
import json
import logging
import io

import urllib
import requests
from flask import Flask, request
from keras.preprocessing.image import (
    ImageDataGenerator,
    load_img,
    array_to_img,
    img_to_array,
)

app = Flask(__name__)

# Constants
FORMAT = os.getenv("FORMAT", "JPEG")
ARG_TYPE = os.getenv("ARG_TYPE", "bytes")

# Environment Variables
host_target = os.environ.get("AIS_TARGET_URL")

logging.info(host_target)

TRANSFORM = os.environ.get("TRANSFORM")
if not host_target:
    raise EnvironmentError("AIS_TARGET_URL environment variable missing")
if not TRANSFORM:
    raise EnvironmentError(
        "TRANSFORM environment variable missing. Check documentation for examples (link)"
    )
transform_dict = json.loads(TRANSFORM)


def transform_image(data: bytes) -> bytes:
    """Process image data as bytes using the specified transformation."""
    try:
        img = load_img(io.BytesIO(data))
        img = img_to_array(img)
        datagen = ImageDataGenerator()
        img = datagen.apply_transform(x=img, transform_parameters=transform_dict)
        img = array_to_img(img)
        buf = io.BytesIO()
        img.save(buf, format=FORMAT)
        return buf.getvalue()
    except Exception as exp:
        logging.error("Error processing data in transform_image: %s", str(exp))
        raise exp


@app.route("/health")
def health_check():
    return "Running"


@app.route("/", defaults={"path": ""}, methods=["PUT", "GET"])
@app.route("/<path:path>", methods=["PUT", "GET"])
def image_handler(path: str):  # pylint: disable=unused-argument
    try:
        if request.method == "PUT":
            post_data = request.data
            processed_data = transform_image(post_data)
            if processed_data is not None:
                return processed_data, 200
            return "Data processing failed", 500

        if request.method == "GET":
            if ARG_TYPE == "url":
                # webdataset
                query_path = request.args.get("url")
                result = transform_image(requests.get(query_path, timeout=5).content)
            else:
                # normal GET - hpull
                object_path = urllib.parse.quote(path, safe="@")
                object_url = f"{host_target}/{object_path}"
                resp = requests.get(object_url, timeout=5)
                if resp.status_code != 200:
                    raise FileNotFoundError(
                        f"Error getting '{path}' from '{host_target}'"
                    )
                result = transform_image(resp.content)

            if result is not None:
                return result, 200
            return "Data processing failed", 500
    except Exception as exp:
        logging.error("Error processing request: %s", str(exp))
        return "Data processing failed", 500
