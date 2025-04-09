#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import logging
import io
from tensorflow.keras.preprocessing.image import (
    ImageDataGenerator,
    load_img,
    array_to_img,
    img_to_array,
)
from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl.etl_templates import KERAS_TRANSFORMER
from aistore.sdk.etl import ETLConfig

from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)
from tests.base import TestBase

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TestKerasTransformer(TestBase):
    """Unit tests for AIStore Keras-based image transformations."""

    def setUp(self):
        """Sets up the test environment by uploading a test image to the bucket."""
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"

        # Upload test image using object writer
        self.test_bck.object(self.test_image_filename).get_writer().put_file(
            self.test_image_source
        )

    def get_transformed_image_local(self) -> bytes:
        """
        Applies the same transformation locally using Keras to compare against the ETL-transformed image.

        Returns:
            bytes: The locally transformed image in JPEG format.
        """
        img = load_img(self.test_image_source)
        img = img_to_array(img)

        # Define ImageDataGenerator transformations
        datagen = ImageDataGenerator()
        transformed_img = datagen.apply_transform(
            x=img,
            transform_parameters={"theta": 40, "brightness": 0.8, "zx": 0.9, "zy": 0.9},
        )

        img = array_to_img(transformed_img)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def get_template(self, comm_type: str, arg_type: str) -> str:
        """
        Generates the transformation template for AIStore ETL.

        Args:
            comm_type (str): The ETL communication type (HPULL, HPUSH).
            arg_type (str): Argument type (`"fqn"` for fully qualified names).

        Returns:
            str: The formatted ETL template.
        """
        template = KERAS_TRANSFORMER.format(
            communication_type=comm_type,
            format="JPEG",
            transform='{"theta":40, "brightness":0.8, "zx":0.9, "zy":0.9}',
            arg_type=arg_type,
        )
        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "keras")
        return template

    def run_keras_test(self, communication_type: str, fqn_flag: bool = False):
        """
        Runs a Keras-based ETL transformation test, comparing AIStore ETL output to local transformation.

        Args:
            communication_type (str): The ETL communication type.
            fqn_flag (bool): Whether to use fully qualified names (FQN).
        """
        arg_type = "fqn" if fqn_flag else ""

        # Generate a unique ETL name
        etl_name = f"keras-transformer-{generate_random_string(5)}"
        self.etls.append(etl_name)

        # Get the transformation template
        template = self.get_template(communication_type, arg_type)

        # Initialize ETL transformation
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type, arg_type=arg_type
        )

        logger.info(
            f"ETL Spec for {communication_type} (ETL: {etl_name}):\n{self.client.etl(etl_name).view()}"
        )

        # Retrieve transformed image from AIStore ETL
        transformed_image_etl = (
            self.test_bck.object(self.test_image_filename)
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )

        # Compare ETL-transformed image with locally transformed image
        self.assertEqual(self.get_transformed_image_local(), transformed_image_etl)

    @cases(
        (ETL_COMM_HPULL, False),
        (ETL_COMM_HPUSH, False),
        (ETL_COMM_HPUSH, True),
        (ETL_COMM_HPULL, True),
    )
    def test_keras_transformer(self, test_case):
        """Tests Keras ETL transformation with different communication types."""
        communication_type, fqn_flag = test_case
        self.run_keras_test(communication_type, fqn_flag)
