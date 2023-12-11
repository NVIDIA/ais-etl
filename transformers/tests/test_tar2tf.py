#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import json
import os
import shutil
import tarfile

import numpy as np
import tensorflow as tf

from PIL import Image
from skimage.metrics import structural_similarity as ssim

from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test

from aistore.sdk.etl_const import ETL_COMM_HREV
from aistore.sdk.etl_templates import TAR2TF


class TestTar2TFTransformer(TestBase):
    def setUp(self):
        super().setUp()
        self.test_tar_filename = "test-tar-single.tar"
        self.test_tar_source = "./resources/test-tar-single.tar"
        self.test_tfrecord_filename = "test-tar-single.tfrecord"
        self.test_bck.object(self.test_tar_filename).put_file(self.test_tar_source)

    def tearDown(self):
        file_path = "./test.tfrecord"
        os.remove(file_path)
        dir_path = "./tmp/"
        shutil.rmtree(dir_path)
        super().tearDown()

    def test_tar2tf_simple(self):
        template = TAR2TF.format(communication_type=ETL_COMM_HREV, arg="", val="")

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "tar2tf")

        self.test_etl.init_spec(communication_type=ETL_COMM_HREV, template=template)

        tfrecord_bytes = (
            self.test_bck.object(self.test_tar_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )
        tfrecord_filename = "test.tfrecord"

        with open(tfrecord_filename, "wb") as f:
            f.write(tfrecord_bytes)

        tfrecord = next(iter(tf.data.TFRecordDataset([tfrecord_filename])))
        example = tf.train.Example()
        example.ParseFromString(tfrecord.numpy())

        cls = example.features.feature["cls"].bytes_list.value[0]
        cls = cls.decode("utf-8")

        transformed_img = example.features.feature["png"].bytes_list.value[0]
        transformed_img = tf.image.decode_image(transformed_img)

        with tarfile.open(self.test_tar_source, "r") as tar:
            tar.extractall(path="./tmp")

        original_img = Image.open("./tmp/tar-single/0001.png")
        original_img_tensor = tf.convert_to_tensor(np.array(original_img))
        with open("./tmp/tar-single/0001.cls", "r", encoding="utf-8") as file:
            original_cls = file.read().strip()

        self.assertTrue(
            np.array_equal(transformed_img.numpy(), original_img_tensor.numpy())
        )
        self.assertEqual(cls, original_cls)

    def test_tar2tf_rotation(self):
        spec = {
            "conversions": [
                {"type": "Decode", "ext_name": "png"},
                {"type": "Rotate", "ext_name": "png", "angle": 30},
            ],
            "selections": [{"ext_name": "png"}, {"ext_name": "cls"}],
        }
        spec = json.dumps(spec)

        template = TAR2TF.format(
            communication_type=ETL_COMM_HREV, arg="-spec", val=spec
        )

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "tar2tf")

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HREV)

        tfrecord_bytes = (
            self.test_bck.object(self.test_tar_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )
        tfrecord_filename = "test.tfrecord"

        with open(tfrecord_filename, "wb") as file:
            file.write(tfrecord_bytes)

        tfrecord = tf.data.TFRecordDataset([tfrecord_filename])
        raw_record = next(iter(tfrecord))
        example = tf.train.Example()
        example.ParseFromString(raw_record.numpy())

        cls = example.features.feature["cls"].bytes_list.value[0]
        cls = cls.decode("utf-8")

        transformed_img = example.features.feature["png"].bytes_list.value[0]
        transformed_img = tf.image.decode_image(transformed_img)

        with tarfile.open(self.test_tar_source, "r") as tar:
            tar.extractall(path="./tmp")

        original_img = Image.open("./tmp/tar-single/0001.png").rotate(
            angle=30, expand=True, fillcolor=(0, 0, 0)
        )
        original_img_tensor = tf.convert_to_tensor(np.array(original_img))
        with open("./tmp/tar-single/0001.cls", "r", encoding="utf-8") as file:
            original_cls = file.read().strip()

        # Ensure both images have the same dimensions
        transformed_img = tf.image.resize(
            transformed_img, original_img_tensor.shape[:2]
        )

        # Calculate the SSIM
        score, _ = ssim(
            transformed_img.numpy(),
            original_img_tensor.numpy(),
            full=True,
            multichannel=True,
            win_size=3,
            data_range=255,
        )

        # Assuming we consider images with SSIM > 0.99 as visually identical
        self.assertTrue(score > 0.99)
        self.assertEqual(cls, original_cls)
