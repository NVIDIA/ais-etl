"""
A basic web server using FastAPI for demonstration purposes.

Steps to run: 
$ # with uvicorn
$ uvicorn main:app --reload 
$ # with multiple uvicorn processes managed by gunicorn
$ gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 

Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
"""
from fastapi import FastAPI, Request

app = FastAPI()

@app.put("/")
@app.put("/{full_path:path}")
async def put_handler(request: Request, full_path: str):
    """
    Handles PUT requests.
    Reads bytes from the request, performs byte transformation,
    and returns the modified bytes.
    """
    # Read bytes from request (request.body)
    # Transform the bytes
    # Return the transformed bytes
    return b"Hello World from PUT!"

@app.get("/")
@app.get("/{full_path:path}")
async def get_handler(request: Request, full_path: str):
    """
    Handles GET requests.
    Retrieves the destination/name of the object from the URL or the full_path variable,
    fetches the object from the AIS target based on the destination/name,
    transforms the bytes, and returns the modified bytes.
    """
    # Get destination/name of object from URL or from full_path variable
    # Fetch object from AIS target based on the destination/name
    # Perform byte transformation
    # Return the transformed bytes
    return b"Hello World from GET!"
