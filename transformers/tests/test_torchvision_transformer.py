#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import io

from PIL import Image
from torchvision import transforms

from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test
from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import TORCHVISION_TRANSFORMER


class TestTransformers(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)

    def simple_torchvision_test(self, communication_type):
        template = TORCHVISION_TRANSFORMER.format(
            communication_type=communication_type,
            transform='{"Resize": {"size": [100, 100]}, "Grayscale": {"num_output_channels": 1}}',
            format="JPEG",
        )

        if self.git_test_mode:
            template = git_test_mode_format_image_tag_test(template, "torchvision")

        # Transform via AIStore
        self.test_etl.init_spec(
            template=template, communication_type=communication_type, timeout="10m"
        )
        etl_transformed_image_bytes = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )

        # Transform via Locally
        transform = transforms.Compose(
            [
                transforms.Resize((100, 100)),  # Resize the image to 100x100 pixels
                transforms.Grayscale(
                    num_output_channels=1
                ),  # Convert the image to grayscale
            ]
        )
        image = Image.open("./resources/test-image.jpg")
        tensor = transforms.ToTensor()(image)
        transformed_tensor = transform(tensor)
        transformed_image = transforms.ToPILImage()(transformed_tensor)
        byte_arr = io.BytesIO()
        transformed_image.save(byte_arr, format="JPEG")
        transformed_image_bytes = byte_arr.getvalue()

        # Compare Results of Separate Transforms
        self.assertEqual(transformed_image_bytes, etl_transformed_image_bytes)

    def test_torch_transformer_simple_hpull(self):
        self.simple_torchvision_test(ETL_COMM_HPULL)

    def test_torch_transformer_simple_hpush(self):
        self.simple_torchvision_test(ETL_COMM_HPUSH)

    def test_torch_transformer_simple_hrev(self):
        self.simple_torchvision_test(ETL_COMM_HREV)
