"""
A simple hello world transformation using FastAPI framework and Gunicorn and Uvicorn webserver.

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

from fastapi import FastAPI, Request, Depends, Response, HTTPException
import aiohttp  # async

app = FastAPI()
host_target = os.environ["AIS_TARGET_URL"]


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
    if not resp or resp.status != 200:
        raise HTTPException(status_code=500, detail="Error retreiving object ({full_path}) from target")
    await resp.read()
    return Response(
        content=b"Hello World!", media_type="application/octet-stream"
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
    await request.body()
    return Response(
        content=b"Hello World!", media_type="application/octet-stream"
    )
