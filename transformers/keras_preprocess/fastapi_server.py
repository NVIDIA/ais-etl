"""
Keras Preprocessing ETL Transformer (FastAPI)

FastAPI-based ETL server that performs image preprocessing using Keras utilities.
Supports various image transformations through the Keras ImageDataGenerator.

Environment Variables:
    AIS_TARGET_URL      - AIStore target URL (required for hpull mode)
    TRANSFORM           - JSON string with transformation parameters for ImageDataGenerator
    FORMAT              - Output image format (default: JPEG)

Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
"""

import io
import json
import os
from urllib.parse import unquote_plus

from tensorflow.keras.utils import (
    load_img,
    array_to_img,
    img_to_array,
)
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer


class KerasPreprocessServer(FastAPIServer):
    """
    FastAPI-based server for Keras image preprocessing transformation.

    Supports various image transformations through Keras ImageDataGenerator.
    Configuration is done via environment variables.
    """

    def __init__(self):
        """
        Initialize the KerasPreprocessServer.

        Fetches configuration from environment variables:
        - TRANSFORM: JSON string with transformation parameters
        - FORMAT: Output image format (default: JPEG)
        """
        super().__init__()

        # Initialize image generator and format
        self._init_transform_config()

    def _init_transform_config(self):
        """Parse and validate transform configuration from environment variables."""
        # Get transform parameters
        transform_str = os.environ.get("TRANSFORM")
        if not transform_str:
            raise EnvironmentError(
                "TRANSFORM environment variable missing. Check documentation for examples."
            )

        try:
            self.transform_params = json.loads(transform_str)
        except json.JSONDecodeError as e:
            self.logger.error("Invalid TRANSFORM JSON: %s", str(e))
            raise

        # Get output format
        self.format = os.environ.get("FORMAT", "JPEG")

        # Initialize the data generator with transform parameters
        self.datagen = ImageDataGenerator(**self.transform_params)

    def transform(self, data: bytes, _path: str, etl_args: str) -> bytes:
        """
        Transform the input image using Keras preprocessing.

        Args:
            data: Input image data as bytes
            _path: Path to the object (unused)
            etl_args: JSON string with transform parameters (optional, overrides env vars)

        Returns:
            Transformed image as bytes

        Raises:
            Exception: If image processing fails
        """
        # Use etl_args if provided, otherwise fall back to environment defaults
        if etl_args:
            try:
                decoded_args = unquote_plus(etl_args)
                transform_params = json.loads(decoded_args)
                datagen = ImageDataGenerator(**transform_params)
            except json.JSONDecodeError:
                datagen = self.datagen
            except (ValueError, TypeError):
                datagen = self.datagen
        else:
            datagen = self.datagen

        try:
            # Load and preprocess image
            img = load_img(io.BytesIO(data))
            img = img_to_array(img)

            # Generate random transform parameters and apply transformation
            transform_params_actual = datagen.get_random_transform(img.shape)
            img = datagen.apply_transform(img, transform_params_actual)

            # Convert back to image and bytes
            img = array_to_img(img)
            buf = io.BytesIO()
            img.save(buf, format=self.format)

            return buf.getvalue()

        except (IOError, ValueError, OSError) as e:
            self.logger.error("Error processing image: %s", str(e), exc_info=True)
            raise


# Create the server instance and expose the FastAPI app
fastapi_server = KerasPreprocessServer()
fastapi_app = fastapi_server.app
