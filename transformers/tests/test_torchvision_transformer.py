"""
Pytest suite for the TorchVision ETL transformer.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import io
import logging
from pathlib import Path
from typing import Dict
import pytest
from PIL import Image
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket
from tests.const import (
    TORCHVISION_TRANSFORMER,
    SERVER_COMMANDS,
    FASTAPI_PARAM_COMBINATIONS,
)

# Configure module-level logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def _upload_test_image(test_bck: Bucket, image_path: Path) -> None:
    """
    Upload test image to the specified bucket.
    """
    filename = "test-image.jpg"
    logger.debug("Uploading %s to bucket %s", filename, test_bck.name)
    test_bck.object(filename).get_writer().put_file(str(image_path))
    return filename


def _get_transformed_image_local(image_path: Path) -> bytes:
    """
    Apply the same transformations locally using PIL.
    This is used to verify the ETL transformer's output.
    """
    # Load image
    image = Image.open(image_path)

    # Resize using PIL directly
    image = image.resize((100, 100), Image.Resampling.BILINEAR)

    # Convert to grayscale
    image = image.convert("L")

    # Save to bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


def _verify_transformed_image(
    test_bck: Bucket,
    image_filename: str,
    etl_name: str,
    local_transformed: bytes,
) -> None:
    """
    Verify that the ETL-transformed image matches the locally transformed image.
    """
    etl_transformed = (
        test_bck.object(image_filename).get_reader(etl=ETLConfig(etl_name)).read_all()
    )
    assert etl_transformed == local_transformed, "ETL and local transformations differ"


def test_torchvision_transformer_local(
    test_bck: Bucket,
    local_files: Dict[str, Path],
) -> None:
    """
    Test the image transformations locally without Docker.
    """
    # Get test image path
    image_path = next(path for path in local_files.values() if path.suffix == ".jpg")

    # Upload test image
    _upload_test_image(test_bck, image_path)

    # Get locally transformed image for comparison
    local_transformed = _get_transformed_image_local(image_path)

    # Load and transform image using PIL directly
    image = Image.open(image_path)

    # Resize
    image = image.resize((100, 100), Image.Resampling.BILINEAR)

    # Convert to grayscale
    image = image.convert("L")

    # Save transformed image
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="JPEG")
    transformed_bytes = img_byte_arr.getvalue()

    # Compare with local transformation
    assert transformed_bytes == local_transformed, "Transformations differ"


@pytest.mark.parametrize("server_type, comm_type, use_fqn", FASTAPI_PARAM_COMBINATIONS)
def test_torchvision_transformer(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_factory,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    Validate the Python-based TorchVision ETL transformer.
    Upload test image, initialize the ETL, then compare transformations.
    """
    # Get test image path
    image_path = next(path for path in local_files.values() if path.suffix == ".jpg")

    # Upload test image
    image_filename = _upload_test_image(test_bck, image_path)

    # Get locally transformed image for comparison
    local_transformed = _get_transformed_image_local(image_path)

    # Build and initialize ETL
    transform_config = {
        "Resize": {"size": [100, 100]},
        "Grayscale": {"num_output_channels": 1},
    }

    # Convert transform config to a string with single quotes
    transform_str = str(transform_config).replace("'", '"')
    # Escape curly braces to avoid format() conflicts
    transform_str_escaped = transform_str.replace("{", "{{").replace("}", "}}")

    # Format the template with actual values
    template = TORCHVISION_TRANSFORMER.format(
        communication_type=comm_type,
        command=SERVER_COMMANDS[server_type],
        direct_put="true",
        format="JPEG",
        transform=transform_str_escaped,
    )

    etl_name = etl_factory(
        tag="torchvision",
        server_type=server_type,
        template=template,
        communication_type=comm_type,
        use_fqn=use_fqn,
        direct_put="true",
    )
    logger.info(
        "Initialized TorchVision ETL '%s' (server=%s, comm=%s, fqn=%s)",
        etl_name,
        server_type,
        comm_type,
        use_fqn,
    )

    # Verify transformations match
    _verify_transformed_image(
        test_bck,
        image_filename,
        etl_name,
        local_transformed,
    )
