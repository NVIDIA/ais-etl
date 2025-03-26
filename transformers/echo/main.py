"""
A simple echo transformation using FastAPI framework with Gunicorn and Uvicorn web server.

Steps to run:
$ # with uvicorn
$ uvicorn main:app --reload
$ # with multiple uvicorn processes managed by gunicorn
$ gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
"""

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring, broad-exception-caught
import os
import urllib.parse

from fastapi import FastAPI, Request, Depends, Response, HTTPException, WebSocket, WebSocketDisconnect
import aiohttp  # async
import logging
import sys
from typing import List

from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return b"Running"


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
    object_path = urllib.parse.quote(full_path, safe="@")
    object_url = f"{host_target}/{object_path}"
    resp = await client.get(object_url)
    if not resp or resp.status != 200:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving object ({full_path}) from target"
        )

    content = await resp.read()
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Length": str(len(content))},  # Set Content-Length
    )


@app.put("/")
@app.put("/{full_path:path}", response_class=Response)
async def put_handler(request: Request):
    """
    Handles PUT requests.
    Reads bytes from the request, performs byte transformation,
    and returns the modified bytes.
    """
    content = await request.body()

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Length": str(len(content))},  # Set Content-Length
    )

# =======================
# WebSocket Endpoint
# =======================

active_connections: List[WebSocket] = []
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to handle live data transformations.
    Clients can send text or binary data, and the transformed output is sent back.
    """
    logger.info(f"New WebSocket connection attempt from: {websocket.client}")

    try:
        await websocket.accept()
        logger.info(f"WebSocket connection established: {websocket.client}")
        active_connections.append(websocket)

        while True:
            data = await websocket.receive_bytes()
            logger.info(f"Received message of length: {len(data)}")
            await websocket.send_bytes(data)

    except WebSocketDisconnect:
        logger.warning(f"WebSocket disconnected: {websocket.client}")
        active_connections.remove(websocket)

    except Exception as e:
        logger.error(f"Unexpected WebSocket error from {websocket.client}: {e}")
        await websocket.close()
