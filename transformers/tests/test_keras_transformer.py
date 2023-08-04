#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import unittest
import io
import os

from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test

from keras.preprocessing.image import (
    ImageDataGenerator,
    load_img,
    array_to_img,
    img_to_array,
)
from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import KERAS_TRANSFORMER


class TestTransformers(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)

    def get_transformed_image_local(self) -> bytes:
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
        return buf.getvalue()

    def get_template(self, comm_type: str) -> str:
        template = KERAS_TRANSFORMER.format(
            communication_type=comm_type,
            format="JPEG",
            transform='{"theta":40, "brightness":0.8, "zx":0.9, "zy":0.9}',
        )
        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "keras")
        return template

    @unittest.skipIf(
        os.getenv("KERAS_ENABLE", "true") == "false",
        "Keras image was not built, skipping keras test",
    )
    def test_keras_transformer_hpull(self):
        self.test_etl.init_spec(template=self.get_template(ETL_COMM_HPULL))
        transformed_image_etl = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )
        self.assertEqual(self.get_transformed_image_local(), transformed_image_etl)

    @unittest.skipIf(
        os.getenv("KERAS_ENABLE", "true") == "false",
        "Keras image was not built, skipping keras test",
    )
    def test_keras_transformer_hrev(self):
        self.test_etl.init_spec(template=self.get_template(ETL_COMM_HREV))
        transformed_image_etl = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )
        self.assertEqual(self.get_transformed_image_local(), transformed_image_etl)

    @unittest.skipIf(
        os.getenv("KERAS_ENABLE", "true") == "false",
        "Keras image was not built, skipping keras test",
    )
    def test_keras_transformer_hpush(self):
        self.test_etl.init_spec(template=self.get_template(ETL_COMM_HPUSH))
        transformed_image_etl = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )
        self.assertEqual(self.get_transformed_image_local(), transformed_image_etl)
