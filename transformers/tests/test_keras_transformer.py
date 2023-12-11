#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring
import logging
import io

from keras.preprocessing.image import (
    ImageDataGenerator,
    load_img,
    array_to_img,
    img_to_array,
)
from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import KERAS_TRANSFORMER
from tests.utils import git_test_mode_format_image_tag_test
from tests.base import TestBase

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


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

    def get_template(self, comm_type: str, arg_type: str) -> str:
        template = KERAS_TRANSFORMER.format(
            communication_type=comm_type,
            format="JPEG",
            transform='{"theta":40, "brightness":0.8, "zx":0.9, "zy":0.9}',
            arg_type=arg_type,
        )
        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "keras")
        return template

    def run_keras_test(self, communication_type: str, fqn_flag: bool = False):
        arg_type = "fqn" if fqn_flag else ""
        template = self.get_template(communication_type, arg_type)
        self.test_etl.init_spec(
            template=template, communication_type=communication_type, arg_type=arg_type
        )

        logger.info(self.test_etl.view())

        transformed_image_etl = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )
        self.assertEqual(self.get_transformed_image_local(), transformed_image_etl)

    def test_keras_transformer_hpull(self):
        self.run_keras_test(communication_type=ETL_COMM_HPULL, fqn_flag=False)

    def test_keras_transformer_hrev(self):
        self.run_keras_test(communication_type=ETL_COMM_HREV, fqn_flag=False)

    def test_keras_transformer_hpush(self):
        self.run_keras_test(communication_type=ETL_COMM_HPUSH, fqn_flag=False)

    def test_keras_transformer_hpush_fqn(self):
        self.run_keras_test(communication_type=ETL_COMM_HPUSH, fqn_flag=True)

    def test_keras_transformer_hpull_fqn(self):
        self.run_keras_test(communication_type=ETL_COMM_HPULL, fqn_flag=True)
