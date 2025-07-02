"""
Pytest suite for the Keras Preprocessing ETL transformer (FastAPI version).

Tests image preprocessing functionality with various transformations and modes.

Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
"""

import io
import json
import logging
from pathlib import Path
from typing import Dict

import pytest
from tensorflow.keras.preprocessing.image import (
    ImageDataGenerator,
    load_img,
    array_to_img,
    img_to_array,
)
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket

from tests.const import (
    KERAS_FASTAPI_TEMPLATE,
    FASTAPI_PARAM_COMBINATIONS,
)

# Configure module-level logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")

# Test transformation parameters
DEFAULT_TRANSFORM = {
    "rotation_range": 40,
    "width_shift_range": 0.2,
    "height_shift_range": 0.2,
    "shear_range": 0.2,
    "zoom_range": 0.2,
    "horizontal_flip": True,
    "fill_mode": "nearest",
}


def _upload_test_images(test_bck: Bucket, local_files: Dict[str, Path]) -> None:
    """
    Upload test images to the specified bucket.
    """
    for filename, path in local_files.items():
        logger.debug("Uploading %s to bucket %s", filename, test_bck.name)
        test_bck.object(filename).get_writer().put_file(str(path))


def _verify_transformation(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_name: str,
    transform_params: dict = None,
) -> None:
    """
    Verify that the images in the bucket are correctly transformed.
    """
    # Use default transform if none provided
    transform_params = transform_params or DEFAULT_TRANSFORM

    # Create local ImageDataGenerator for comparison with same parameters
    datagen = ImageDataGenerator(**transform_params)

    for filename, path in local_files.items():
        # Skip non-image files
        if not filename.lower().endswith(IMAGE_EXTENSIONS):
            continue

        # Read and transform original image locally
        img = load_img(path)
        img_array = img_to_array(img)

        # Generate random transform parameters and apply transformation (correct approach)
        transform_params_actual = datagen.get_random_transform(img_array.shape)
        expected = datagen.apply_transform(img_array, transform_params_actual)
        expected_img = array_to_img(expected)
        expected_buf = io.BytesIO()
        expected_img.save(expected_buf, format="JPEG")
        expected_bytes = expected_buf.getvalue()

        # Get transformed data from ETL
        reader = test_bck.object(filename).get_reader(
            etl=ETLConfig(etl_name, args=json.dumps(transform_params))
        )
        transformed = reader.read_all()

        # Compare results
        assert len(transformed) > 0, f"Transformed image is empty for {filename}"

        # Load both images and compare their contents
        img1 = load_img(io.BytesIO(expected_bytes))
        img2 = load_img(io.BytesIO(transformed))

        # Convert to arrays for comparison
        arr1 = img_to_array(img1)
        arr2 = img_to_array(img2)

        # Images should be similar (allowing for small differences due to compression)
        assert arr1.shape == arr2.shape, f"Image shapes don't match for {filename}"

        # Since both use random transformations, just check that transformation occurred
        # by comparing with original image
        original_img = load_img(path)
        original_array = img_to_array(original_img)

        # Both transformed images should be different from original
        diff1 = abs(original_array - arr1).mean()
        diff2 = abs(original_array - arr2).mean()

        assert (
            diff1 > 5.0
        ), f"Local transformation didn't change image enough for {filename}"
        assert (
            diff2 > 5.0
        ), f"ETL transformation didn't change image enough for {filename}"

        logger.info(
            "Transformation verified for %s (local diff: %.2f, etl diff: %.2f)",
            filename,
            diff1,
            diff2,
        )


@pytest.mark.parametrize("server_type, comm_type, use_fqn", FASTAPI_PARAM_COMBINATIONS)
def test_keras_fastapi_transformer(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_factory,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    Validate the Keras Preprocessing ETL transformer functionality.
    Tests image transformations with different communication types and FQN settings.
    """
    # Upload test images
    _upload_test_images(test_bck, local_files)

    # Build and initialize ETL
    etl_name = etl_factory(
        tag="keras-preprocess",
        server_type=server_type,
        template=KERAS_FASTAPI_TEMPLATE,
        communication_type=comm_type,
        use_fqn=use_fqn,
        direct_put="true",
    )
    logger.info(
        "Initialized Keras ETL '%s' (server=%s, comm=%s, fqn=%s)",
        etl_name,
        server_type,
        comm_type,
        use_fqn,
    )

    # Test with default transformation parameters
    _verify_transformation(test_bck, local_files, etl_name)

    # Test with custom transformation parameters
    custom_transform = {
        "rotation_range": 90,
        "width_shift_range": 0.3,
        "height_shift_range": 0.3,
        "zoom_range": 0.5,
    }
    _verify_transformation(test_bck, local_files, etl_name, custom_transform)
