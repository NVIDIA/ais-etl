#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import json
import os
import shutil
import tarfile

import numpy as np
import tensorflow as tf

from PIL import Image
from skimage.metrics import structural_similarity as ssim

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL
from aistore.sdk.etl.etl_templates import TAR2TF
from aistore.sdk.etl import ETLConfig

from tests.base import TestBase
from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)


class TestTar2TFTransformer(TestBase):
    """Unit tests for the TAR-to-TFRecord AIStore ETL Transformer."""

    def setUp(self):
        """Sets up the test environment by uploading a test tar file to the bucket."""
        super().setUp()
        self.test_tar_filename = "test-tar-single.tar"
        self.test_tar_source = "./resources/test-tar-single.tar"
        self.test_bck.object(self.test_tar_filename).put_file(self.test_tar_source)

    def tearDown(self):
        """Cleans up generated files and directories after each test."""
        try:
            os.remove("./test.tfrecord")
        except FileNotFoundError:
            pass
        shutil.rmtree("./tmp/", ignore_errors=True)
        super().tearDown()

    def run_tar2tf_test(self, spec=None):
        """
        Runs a TAR-to-TFRecord transformation test with optional modifications.

        Args:
            spec (dict, optional): JSON spec for transformations. Defaults to None.
        """
        template = TAR2TF.format(
            communication_type=ETL_COMM_HPULL,
            arg="-spec" if spec else "",
            val=json.dumps(spec) if spec else "",
        )

        if self.git_test_mode == "true":
            template = format_image_tag_for_git_test_mode(template, "tar2tf")

        # Initialize ETL transformation
        etl_name = f"tar2tf-{generate_random_string(5)}"
        self.etls.append(etl_name)
        self.client.etl(etl_name).init_spec(
            communication_type=ETL_COMM_HPULL, template=template
        )

        # Retrieve transformed TFRecord bytes
        tfrecord_bytes = (
            self.test_bck.object(self.test_tar_filename)
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )

        # Save TFRecord to a file
        tfrecord_filename = "test.tfrecord"
        with open(tfrecord_filename, "wb") as f:
            f.write(tfrecord_bytes)

        # Read the TFRecord file
        tfrecord = next(iter(tf.data.TFRecordDataset([tfrecord_filename])))
        example = tf.train.Example()
        example.ParseFromString(tfrecord.numpy())

        # Extract class label from TFRecord
        cls = example.features.feature["cls"].bytes_list.value[0].decode("utf-8")

        # Extract transformed image
        transformed_img = example.features.feature["png"].bytes_list.value[0]
        transformed_img = tf.image.decode_image(transformed_img)

        # Extract the original image and class label from the tar file
        with tarfile.open(self.test_tar_source, "r") as tar:
            tar.extractall(path="./tmp")

        original_img = Image.open("./tmp/tar-single/0001.png")
        original_img_tensor = tf.convert_to_tensor(np.array(original_img))

        with open("./tmp/tar-single/0001.cls", "r", encoding="utf-8") as file:
            original_cls = file.read().strip()

        if spec:
            # Apply transformation manually for comparison
            if "Rotate" in json.dumps(spec):
                angle = spec["conversions"][1]["angle"]
                original_img = original_img.rotate(
                    angle=angle, expand=True, fillcolor=(0, 0, 0)
                )
                original_img_tensor = tf.convert_to_tensor(np.array(original_img))

                # Ensure both images have the same dimensions before comparison
                transformed_img = tf.image.resize(
                    transformed_img, original_img_tensor.shape[:2]
                )

                # Compute Structural Similarity Index (SSIM)
                score, _ = ssim(
                    transformed_img.numpy(),
                    original_img_tensor.numpy(),
                    full=True,
                    multichannel=True,
                    win_size=3,
                    data_range=255,
                )

                # Assume SSIM > 0.99 indicates a visually identical match
                self.assertTrue(score > 0.99)

        else:
            # Verify image content matches without transformations
            self.assertTrue(
                np.array_equal(transformed_img.numpy(), original_img_tensor.numpy())
            )

        self.assertEqual(cls, original_cls)

    @cases(
        (None),
        (
            {
                "conversions": [
                    {"type": "Decode", "ext_name": "png"},
                    {"type": "Rotate", "ext_name": "png", "angle": 30},
                ],
                "selections": [{"ext_name": "png"}, {"ext_name": "cls"}],
            }
        ),
    )
    def test_tar2tf_transformations(self, spec):
        """Tests TAR-to-TFRecord transformation with different configurations."""
        self.run_tar2tf_test(spec)
