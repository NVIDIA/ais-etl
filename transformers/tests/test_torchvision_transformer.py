#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import io
from PIL import Image
from torchvision import transforms

from tests.base import TestBase
from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)
from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl.etl_templates import TORCHVISION_TRANSFORMER
from aistore.sdk.etl import ETLConfig


class TestTorchVisionTransformer(TestBase):
    """Unit tests for TorchVision-based image transformations using AIStore ETL."""

    def setUp(self):
        """Set up test environment by uploading a test image to the bucket."""
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"

        self.test_bck.object(self.test_image_filename).get_writer().put_file(
            self.test_image_source
        )

    def run_torchvision_test(self, communication_type):
        """
        Compares AIStore ETL-transformed images with locally transformed images.

        Args:
            communication_type (str): The ETL communication type (HPULL, HPUSH).
        """
        etl_name = f"torchvision-transformer-{generate_random_string(5)}"
        self.etls.append(etl_name)

        # Define AIStore ETL transformation template
        template = TORCHVISION_TRANSFORMER.format(
            communication_type=communication_type,
            transform='{"Resize": {"size": [100, 100]}, "Grayscale": {"num_output_channels": 1}}',
            format="JPEG",
        )

        # Modify template for Git test mode
        if self.git_test_mode:
            template = format_image_tag_for_git_test_mode(template, "torchvision")

        # Initialize ETL and apply transformation via AIStore
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type, timeout="10m"
        )

        etl_transformed_image_bytes = (
            self.test_bck.object(self.test_image_filename)
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )

        # Perform the same transformation locally using TorchVision
        transformed_image_bytes = self.get_transformed_image_local()

        # Assert that AIStore ETL and local transformations produce identical outputs
        self.assertEqual(transformed_image_bytes, etl_transformed_image_bytes)

    def get_transformed_image_local(self) -> bytes:
        """
        Applies the same transformation locally using TorchVision to compare against AIStore ETL output.

        Returns:
            bytes: The locally transformed image in JPEG format.
        """
        transform = transforms.Compose(
            [
                transforms.Resize((100, 100)),  # Resize to 100x100 pixels
                transforms.Grayscale(num_output_channels=1),  # Convert to grayscale
            ]
        )
        image = Image.open(self.test_image_source)
        transformed_tensor = transform(transforms.ToTensor()(image))
        transformed_image = transforms.ToPILImage()(transformed_tensor)

        # Convert transformed image to bytes
        byte_arr = io.BytesIO()
        transformed_image.save(byte_arr, format="JPEG")
        return byte_arr.getvalue()

    @cases(
        ETL_COMM_HPULL,
        ETL_COMM_HPUSH,
    )
    def test_torchvision_transform(self, communication_type):
        """Runs the TorchVision ETL transformation for different communication types."""
        self.run_torchvision_test(communication_type)
