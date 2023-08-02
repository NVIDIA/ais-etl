#!/usr/bin/env python
#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring, broad-exception-caught

import os
import json
import logging
import io

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
    except Exception as e:
        logging.error("Error processing data: %s", str(e))
        raise


@app.route("/health")
def health_check():
    return "OK"


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
                # Need this for webdataset
                query_path = request.args.get("url")
                result = transform_image(requests.get(query_path, timeout=5).content)
            else:
                query_path = host_target + request.path
                content = requests.get(query_path, timeout=5).content
                result = transform_image(content)

            if result is not None:
                return result, 200
            return "Data processing failed", 500

    except Exception as e:
        logging.error("Error processing request: %s", str(e))
        return "Data processing failed", 500


if __name__ == "__main__":
    # run the app using gunicorn
    app.run()
