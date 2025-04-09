"""
Transorming images with Keras API using FastAPI framework and Gunicorn and Uvicorn webserver.

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

from fastapi import FastAPI, Request, Depends, Response
import aiohttp  # async
from PIL import Image
from torchvision import transforms

app = FastAPI()

host_target = os.environ["AIS_TARGET_URL"]
transform_format = os.environ["FORMAT"]
transform_json = os.environ["TRANSFORM"]
transform_dict = json.loads(transform_json)

# Create a list to hold the transformations
transform_list = []

# Add each transformation to the list
for transform_name, params in transform_dict.items():
    # Get the transform class from torchvision.transforms
    transform_class = getattr(transforms, transform_name)

    # Create an instance of the transform class with the specified parameters
    transform_instance = transform_class(**params)

    # Add the transform instance to the list
    transform_list.append(transform_instance)

# Combine the transformations into a single transform
transform = transforms.Compose(transform_list)


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


async def transform_image(image_bytes: bytes) -> bytes:
    # Convert bytes to PIL Image
    image = Image.open(io.BytesIO(image_bytes))
    # Convert the PIL image to a PyTorch tensor
    tensor_transform = transforms.ToTensor()
    tensor = tensor_transform(image)
    # Apply the transformation
    transformed_tensor = transform(tensor)
    # Convert the transformed tensor back to a PIL image
    pil_transform = transforms.ToPILImage()
    transformed_image = pil_transform(transformed_tensor)
    # Convert the PIL image back to bytes
    byte_arr = io.BytesIO()
    transformed_image.save(byte_arr, format=transform_format)
    # Get the byte array
    transformed_image_bytes = byte_arr.getvalue()
    return transformed_image_bytes


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
    object_path = urllib.parse.quote(full_path, safe="@")
    object_url = f"{host_target}/{object_path}"
    resp = await client.get(object_url)
    body = await resp.read()

    return Response(
        content=await transform_image(body), media_type="application/octet-stream"
    )


@app.put("/")
@app.put("/{full_path:path}", response_class=Response)
async def put_handler(request: Request):
    """
    Handles PUT requests.
    Reads bytes from the request, performs byte transformation,
    and returns the modified bytes.
    """
    # Read bytes from request (request.body)
    # Transform the bytes
    # Return the transformed bytes
    body = await request.body()
    return Response(
        content=await transform_image(body), media_type="application/octet-stream"
    )
