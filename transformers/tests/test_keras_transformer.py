#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import unittest
import io
import os
from aistore.sdk.etl_const import ETL_COMM_HPULL
from aistore.sdk.etl_templates import KERAS_TRANSFORMER

from keras.preprocessing.image import (
    ImageDataGenerator,
    load_img,
    array_to_img,
    img_to_array,
)
from test_base import TestBase
from utils import git_test_mode_format_image_tag_test


class TestTransformers(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)

    @unittest.skipIf(
        os.getenv("KERAS_ENABLE", "true") == "false",
        "Keras image was not built, skipping keras test",
    )
    def test_keras_transformer(self):
        template = KERAS_TRANSFORMER.format(
            communication_type=ETL_COMM_HPULL,
            format="JPEG",
            transform='{"theta":40, "brightness":0.8, "zx":0.9, "zy":0.9}',
        )
        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "keras")

        self.test_etl.init_spec(template=template)

        # transformed image - etl
        transformed_image_etl = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )

        # transformed image - local
        img = load_img(self.test_image_source)
        img = img_to_array(img)
        datagen = ImageDataGenerator()
        rotate = datagen.apply_transform(
            x=img,
            transform_parameters={"theta": 40, "brightness": 0.8, "zx": 0.9, "zy": 0.9},
        )
        img = array_to_img(rotate)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        transformed_image_local = buf.getvalue()

        self.assertEqual(transformed_image_local, transformed_image_etl)
