"""
Transorming images with Keras API using FastAPI framework and Gunivorn and Uvicorn webserver.

Steps to run: 
$ # with uvicorn
$ uvicorn main:app --reload 
$ # with multiple uvicorn processes managed by gunicorn
$ gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 

Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
"""
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring, broad-exception-caught
import os
import urllib.parse
import json
import io
import logging

from fastapi import FastAPI, Request, Depends, Response
import aiohttp  # async

from tensorflow.keras.utils import (
    load_img,
    array_to_img,
    img_to_array,
)

from keras.preprocessing.image import ImageDataGenerator

app = FastAPI()

# Constants
FORMAT = os.getenv("FORMAT", "JPEG")
arg_type = os.getenv("ARG_TYPE", "")

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


class HttpClient:
    session: aiohttp.ClientSession = None

    def start(self):
        self.session = aiohttp.ClientSession()

    async def stop(self):
        await self.session.close()
        self.session = None

    def __call__(self) -> aiohttp.ClientSession:
        assert self.session is not None
        return self.session


http_client = HttpClient()


@app.on_event("startup")
async def startup():
    http_client.start()


@app.get("/health")
async def health():
    return b"Ok"


async def transform_image(data: bytes) -> bytes:
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


@app.get("/")
@app.get("/{full_path:path}", response_class=Response)
async def get_handler(
    full_path: str, client: aiohttp.ClientSession = Depends(http_client)
):
    """
    Handles GET requests.
    Retrieves the destination/name of the object from the URL or the full_path variable,
    fetches the object from the AIS target based on the destination/name,
    transforms the bytes, and returns the modified bytes.
    """
    # Get destination/name of object from URL or from full_path variable
    # Fetch object from AIS target based on the destination/name
    # Transform the bytes
    # Return the transformed bytes
    if arg_type.lower() == "fqn":
        with open(full_path, "rb") as file:
            body = file.read()
    else:
        object_path = urllib.parse.quote(full_path, safe="@")
        object_url = f"{host_target}/{object_path}"
        resp = await client.get(object_url)
        body = await resp.read()

    return Response(
        content=await transform_image(body), media_type="application/octet-stream"
    )


@app.put("/")
@app.put("/{full_path:path}", response_class=Response)
async def put_handler(request: Request, full_path: str):
    """
    Handles PUT requests.
    Reads bytes from the request, performs byte transformation,
    and returns the modified bytes.
    """
    # Read bytes from request (request.body)
    # Transform the bytes
    # Return the transformed bytes
    if arg_type.lower() == "fqn":
        with open(full_path, "rb") as file:
            body = file.read()
    else:
        body = await request.body()
    return Response(
        content=await transform_image(body), media_type="application/octet-stream"
    )
