#!/usr/bin/env python

#
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
#

"""
Torchvision ETL Transformer (FastAPI)

FastAPI-based ETL server that transforms images using torchvision library.
Supports configurable image transformations and compression.

Environment Variables:
    TRANSFORM          - JSON string with torchvision transformations (required)
                        Ex: {"Resize": {"size": [224, 224]}, "Grayscale": {"num_output_channels": 1}}
    FORMAT             - Output image format (JPEG, PNG, etc.)
                        Default: "JPEG"

Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
"""

import json
import io
import os
import sys
from collections.abc import Iterable
from typing import Optional

from PIL import Image
from torchvision import transforms
from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer

# Patch collections.Iterable for Python 3.13 compatibility
if sys.version_info >= (3, 13):
    import collections

    collections.Iterable = Iterable


class TorchvisionServer(FastAPIServer):
    """Server for applying torchvision transforms to images."""

    def __init__(self):
        """Initialize the server with transform configuration."""
        super().__init__()
        self.transform_format = os.environ.get("FORMAT", "JPEG")
        transform_config = os.environ.get("TRANSFORM")
        if not transform_config:
            raise ValueError("TRANSFORM environment variable is required")
        self.transform_pipeline = self._create_transform_pipeline(
            transform_config
        )

    def _create_transform_pipeline(self, transform_config: str) -> transforms.Compose:
        """Create a torchvision transform pipeline from configuration."""
        try:
            config_dict = json.loads(transform_config)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in transform configuration: {e}"
            ) from e
            
        transform_list = []
        for transform_name, params in config_dict.items():
            try:
                transform_class = getattr(transforms, transform_name)
            except AttributeError as exc:
                raise ValueError(f"Unknown transform: {transform_name}") from exc
            try:
                transform_list.append(transform_class(**params))
            except Exception as e:
                raise ValueError(f"Invalid parameters for {transform_name}: {e}") from e
        return transforms.Compose(transform_list)

    def transform(
        self, data: bytes, _path: str, etl_args: Optional[str] = None
    ) -> bytes:  # pylint: disable=unused-argument
        """
        Transform the input image data using the configured transform pipeline.

        Args:
            data: Input image data as bytes
             _path: Path to the object (unused)
            etl_args: Optional JSON string with additional arguments
                     Ex: {"format": "PNG"}

        Returns:
            Transformed image data as bytes

        Raises:
            RuntimeError: If image transformation fails
        """
        try:
            # Parse etl_args if provided
            format_override = None
            if etl_args:
                try:
                    args_dict = json.loads(etl_args)
                    format_override = args_dict.get("format")
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON and use default format

            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(data))

            # Apply transform pipeline
            transformed_image = self.transform_pipeline(image)

            # Convert back to bytes
            output_format = format_override or self.transform_format
            img_byte_arr = io.BytesIO()
            transformed_image.save(img_byte_arr, format=output_format)
            return img_byte_arr.getvalue()

        except Exception as e:
            raise RuntimeError(f"Error transforming image: {str(e)}") from e

    def get_mime_type(self) -> str:
        """
        Return the MIME type for the transformed image data.
        """
        return "image/jpeg"


# Create the server instance and expose the FastAPI app
fastapi_server = TorchvisionServer()
fastapi_app = fastapi_server.app
