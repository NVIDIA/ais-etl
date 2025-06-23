"""
Face Detection ETL transformer (FastAPI)

FastAPI-based ETL server that detects faces in images using SSD (Single Shot MultiBox Detector) model.
Supports both individual images and tar/webdataset archives.

Environment:
  FORMAT: Output image format (e.g., 'jpg', 'png')
  ARG_TYPE: Type of argument passed ('fqn' for file path or empty for URL)
  AIS_TARGET_URL: URL of the AIS target

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import io
import logging
import tarfile

import cv2
import numpy as np
from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer

# Constants
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")
TAR_EXTENSIONS = [".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"]


class FaceDetection(FastAPIServer):
    """
    ETL server that detects faces in images using SSD model.
    Supports both individual images and tar/webdataset archives.
    """

    def __init__(
        self,
    ) -> None:
        """
        Initialize the FaceDetection server.

        Args:
            port: TCP port to listen on (default 8000).
        """
        super().__init__()
        self.logger.setLevel(logging.DEBUG)

        # Load environment variables
        self.format = os.environ.get("FORMAT", "jpg")
        self.arg_type = os.environ.get("ARG_TYPE", "")
        self.host_target = os.environ.get("AIS_TARGET_URL")

        # Load the face detection model
        self.model = cv2.dnn.readNetFromCaffe(
            "./model/architecture.txt", "./model/weights.caffemodel"
        )

    def _transform_image(self, image_bytes: bytes) -> bytes:
        """
        Detect faces in a single image.

        Args:
            image_bytes: Raw image data.

        Returns:
            Processed image with detected faces marked.
        """
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), -1)
        image_height, image_width, _ = image.shape
        output_image = image.copy()

        # Preprocess image for the model
        preprocessed_image = cv2.dnn.blobFromImage(
            image,
            scalefactor=1.0,
            size=(300, 300),
            mean=(104.0, 117.0, 123.0),
            swapRB=False,
            crop=False,
        )

        # Run face detection
        self.model.setInput(preprocessed_image)
        results = self.model.forward()

        # Draw rectangles around detected faces
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

        # Encode and return the processed image
        _, encoded_image = cv2.imencode(f".{self.format}", output_image)
        return encoded_image.tobytes()

    def _transform_tar(self, data: bytes) -> bytes:
        """
        Process a tar archive containing images.

        Args:
            data: Raw tar archive data as bytes.

        Returns:
            Processed tar archive with face detection applied to each image.
        """
        input_buffer = io.BytesIO(data)
        output_buffer = io.BytesIO()

        with tarfile.open(fileobj=input_buffer, mode="r") as input_tar, tarfile.open(
            fileobj=output_buffer, mode="w"
        ) as output_tar:

            # Process each file in the tar
            for member in input_tar.getmembers():
                if member.isfile():
                    file_data = input_tar.extractfile(member).read()
                    if member.name.lower().endswith(IMAGE_EXTENSIONS):
                        processed_data = self._transform_image(file_data)
                        member.size = len(processed_data)
                        output_tar.addfile(member, io.BytesIO(processed_data))
                    else:
                        output_tar.addfile(member, io.BytesIO(file_data))

        # Return the processed tar data
        output_buffer.seek(0)
        result_data = output_buffer.read()
        output_buffer.close()
        input_buffer.close()

        return result_data

    def _is_tar_file(self, path: str) -> bool:
        """
        Determine if the file is a tar archive based on the path extension.

        Args:
            path: File path or object key.

        Returns:
            True if the file appears to be a tar archive, False otherwise.
        """
        path_lower = path.lower()
        return any(path_lower.endswith(ext) for ext in TAR_EXTENSIONS)

    def transform(
        self,
        data: bytes,
        path: str,
        _etl_args: str,
    ) -> bytes:
        """
        Transform the input data by detecting faces.

        Args:
            data: Raw request payload (image data).
            path: Request path or object key.
            etl_args: Optional arguments (unused).

        Returns:
            Processed image data with detected faces marked.
        """
        if self._is_tar_file(path):
            return self._transform_tar(data)
        return self._transform_image(data)


# instantiate and expose
fastapi_server = FaceDetection()
fastapi_app = fastapi_server.app
