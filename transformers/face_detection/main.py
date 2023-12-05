"""
Detecting Faces w/ SSD model (SSD: Single Shot MultiBox Detector) using FastAPI framework 
and Gunivorn and Uvicorn webserver.

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

import aiofiles
from fastapi import FastAPI, Request, Depends, Response
import aiohttp  # async
import cv2
import numpy as np

app = FastAPI()

host_target = os.environ["AIS_TARGET_URL"]
FORMAT = os.environ["FORMAT"]
arg_type = os.getenv("ARG_TYPE", "")


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
    return b"Running"


cvNet = cv2.dnn.readNetFromCaffe(
    "./model/architecture.txt", "./model/weights.caffemodel"
)


async def transform_image(image_bytes: bytes) -> bytes:
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), -1)
    image_height, image_width, _ = image.shape
    output_image = image.copy()
    preprocessed_image = cv2.dnn.blobFromImage(
        image,
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 117.0, 123.0),
        swapRB=False,
        crop=False,
    )
    cvNet.setInput(preprocessed_image)
    results = cvNet.forward()

    for face in results[0][0]:
        face_confidence = face[2]
        if face_confidence > 0.6:
            bbox = face[3:]
            x_1 = int(bbox[0] * image_width)
            y_1 = int(bbox[1] * image_height)
            x_2 = int(bbox[2] * image_width)
            y_2 = int(bbox[3] * image_height)
            cv2.rectangle(
                output_image,
                pt1=(x_1, y_1),
                pt2=(x_2, y_2),
                color=(0, 255, 0),
                thickness=image_width // 200,
            )
    _, encoded_image = cv2.imencode(f".{FORMAT}", output_image)
    return encoded_image.tobytes()


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
        async with aiofiles.open(full_path, "rb") as file:
            body = await file.read()
    else:
        object_path = urllib.parse.quote(full_path, safe="@")
        object_url = f"{host_target}/{object_path}"
        resp = await client.get(object_url)
        body = await resp.read()

    return Response(
        content=await transform_image(body),
        media_type="application/octet-stream",
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
    if arg_type.lower() == "fqn":
        async with aiofiles.open(full_path, "rb") as file:
            body = await file.read()
    else:
        body = await request.body()

    # Transform the bytes
    # Return the transformed bytes
    return Response(
        content=await transform_image(body),
        media_type="application/octet-stream",
    )
