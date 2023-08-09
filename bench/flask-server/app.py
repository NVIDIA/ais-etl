"""
A basic web server using Flask for demonstration purposes.

Steps to run:
$ # with built-in flask server
$ flask --app app run
$ # with gunicorn
$ gunicorn -w 4 'app:app'

Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
"""
import logging
from flask import Flask, request

app = Flask(__name__)


@app.route("/", defaults={"path": ""}, methods=["PUT", "GET"])
@app.route("/<path:path>", methods=["PUT", "GET"])
def image_handler(path):
    try:
        if request.method == "PUT":
            # Read the request body
            # Transform the bytes
            # Return the transformed bytes
            transformed_data = b"Hello World!"
            return transformed_data, 200

        elif request.method == "GET":
            # Get the destination/name of the object from the URL or the path variable
            # Fetch the object from the AIS target based on the destination/name
            # Use request.get(ais_target_url + "/" + path).get to get the object
            # Transform the bytes
            # Return the transformed bytes
            transformed_data = b"Hello World!"
            return transformed_data, 200

    except Exception as exception:
        logging.error("Error processing request: %s", str(exception))
        return "Data processing failed", 500


if __name__ == "__main__":
    app.run()
