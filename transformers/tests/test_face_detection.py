"""
Pytest suite for the Face Detection ETL transformer.

Tests face detection functionality in both single image and tar/webdataset modes.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
import cv2
import numpy as np
import io
import tarfile
from pathlib import Path
from typing import Dict

import pytest
import webdataset as wds
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket

from tests.const import FASTAPI_PARAM_COMBINATIONS

# Configure module-level logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def _upload_test_files(test_bck: Bucket, local_files: Dict[str, Path]) -> None:
    """Upload files to the specified bucket."""
    for filename, path in local_files.items():
        test_bck.object(filename).get_writer().put_file(str(path))


def _verify_face_detection(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_name: str,
    _output_format: str = "jpg",
) -> None:
    """
    Verify that faces are correctly detected in the images.

    Args:
        test_bck: Test bucket containing input images
        local_files: Dictionary mapping filenames to local paths
        etl_name: Name of the ETL to use
        output_format: Expected output image format
    """
    for filename, path in local_files.items():
        # Skip non-image files
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        # Get transformed image
        reader = test_bck.object(filename).get_reader(etl=ETLConfig(etl_name))
        transformed = reader.read_all()

        # Decode the transformed image
        image = cv2.imdecode(np.frombuffer(transformed, np.uint8), -1)

        # Basic verification checks
        assert image is not None, f"Failed to decode transformed image for {filename}"
        assert (
            len(image.shape) == 3
        ), f"Expected color image, got shape {image.shape} for {filename}"
        assert image.shape[2] in [
            3,
            4,
        ], f"Expected 3 (RGB) or 4 (RGBA) color channels, got {image.shape[2]} for {filename}"

        # Check for green rectangles (face detection markers)
        # Ensure image is 8-bit for HSV conversion (workaround for Docker image issue)
        if image.dtype != np.uint8:
            if image.dtype == np.uint16:
                image = (image / 256).astype(np.uint8)
            else:
                image = cv2.convertScaleAbs(image)

        # Convert to HSV for easier color detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, (35, 50, 50), (85, 255, 255))
        has_green = np.any(green_mask)

        assert (
            has_green
        ), f"No face detection markers (green rectangles) found in {filename}"


def _verify_tar_face_detection(
    test_bck: Bucket,
    tar_filename: str,
    etl_name: str,
    output_format: str = "jpg",
) -> None:
    """
    Verify face detection in a tar/webdataset archive.

    Args:
        test_bck: Test bucket containing the tar file
        tar_filename: Name of the tar file in the bucket
        etl_name: Name of the ETL to use
        output_format: Expected output image format
    """
    # Get transformed tar
    reader = test_bck.object(tar_filename).get_reader(etl=ETLConfig(etl_name))
    transformed_tar = reader.read_all()

    # Read tar contents
    tar_buffer = io.BytesIO(transformed_tar)
    with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
        for member in tar.getmembers():
            if not member.name.lower().endswith(f".{output_format}"):
                continue

            # Extract and verify each image
            f = tar.extractfile(member)
            if f is None:
                continue

            image_data = f.read()
            image = cv2.imdecode(np.frombuffer(image_data, np.uint8), -1)

            # Basic verification checks
            assert image is not None, f"Failed to decode image {member.name} from tar"
            assert (
                len(image.shape) == 3
            ), f"Expected color image, got shape {image.shape} for {member.name}"
            assert image.shape[2] in [
                3,
                4,
            ], f"Expected 3 (RGB) or 4 (RGBA) color channels, got {image.shape[2]} for {member.name}"

            # Check for green rectangles (face detection markers)
            # Ensure image is 8-bit for HSV conversion (workaround for Docker image issue)
            if image.dtype != np.uint8:
                if image.dtype == np.uint16:
                    image = (image / 256).astype(np.uint8)
                else:
                    image = cv2.convertScaleAbs(image)

            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            green_mask = cv2.inRange(hsv, (35, 50, 50), (85, 255, 255))
            has_green = np.any(green_mask)

            assert has_green, f"No face detection markers found in {member.name}"


@pytest.mark.parametrize("server_type, comm_type, use_fqn", FASTAPI_PARAM_COMBINATIONS)
@pytest.mark.parametrize("output_format", ["jpg", "png"])
def test_face_detection(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_factory,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
    output_format: str,
) -> None:
    """
    Validate the Face Detection ETL transformer.
    Tests face detection on sample images with various configurations.
    """
    # Upload inputs
    _upload_test_files(test_bck, local_files)

    # Build and initialize ETL
    etl_name = etl_factory(
        tag="face-detection",
        server_type=server_type,
        comm_type=comm_type,
        arg_type="fqn" if use_fqn else "",
        direct_put=True,
        format=output_format,
    )

    _verify_face_detection(
        test_bck,
        local_files,
        etl_name,
        output_format,
    )


@pytest.mark.parametrize("server_type, comm_type, use_fqn", FASTAPI_PARAM_COMBINATIONS)
@pytest.mark.parametrize("output_format", ["jpg", "png"])
def test_face_detection_tar_runtime(
    test_bck: Bucket,
    etl_factory,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
    output_format: str,
) -> None:
    """
    Validate the Face Detection ETL transformer in tar/webdataset mode.
    Creates the input tar file at runtime using a test image.
    """
    image_path = Path(__file__).parent / "resources" / "test-face-detection.png"
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tarinfo = tarfile.TarInfo(name="face.png")
        tarinfo.size = len(image_bytes)
        tar.addfile(tarinfo, io.BytesIO(image_bytes))
    tar_stream.seek(0)

    tar_object_name = "test-face-detection.tar"

    test_bck.object(tar_object_name).get_writer().put_content(tar_stream.getvalue())

    etl_name = etl_factory(
        tag="face-detection",
        server_type=server_type,
        comm_type=comm_type,
        arg_type="fqn" if use_fqn else "",
        direct_put=True,
        format=output_format,
    )

    _verify_tar_face_detection(
        test_bck,
        tar_object_name,
        etl_name,
        output_format,
    )
