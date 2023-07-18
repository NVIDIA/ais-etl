#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import hashlib
import json
import os
import random
import shutil
import string
import tarfile
import time
import unittest

import numpy as np
import tensorflow as tf

from PIL import Image
from skimage.metrics import structural_similarity as ssim

from aistore import Client
from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HREV
from aistore.sdk.etl_templates import GO_ECHO, ECHO, HELLO_WORLD, MD5, TAR2TF

class TestTransformers(unittest.TestCase):
    def setUp(self):
        self.endpoint = os.environ.get("AIS_ENDPOINT", "http://192.168.49.2:8080")
        self.client = Client(self.endpoint)
        self.src_bck = self.client.bucket("src").create()
        self.dest_bck = self.client.bucket("dest").create()

        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_tar_filename = "test-tar-single.tar"
        self.test_tar_source = "./resources/test-tar-single.tar"
        self.test_tfrecord_filename = "test-tar-single.tfrecord"

        self.num_etls = len(self.client.cluster().list_running_etls())

        self.test_etl = self.client.etl("test-etl-" + self.generate_random_str()) # TODO: Check stop/delete (start)

    def tearDown(self):
        self.src_bck.delete()
        self.dest_bck.delete()
        self.test_etl.stop()
        self.test_etl.delete()

    def tar2tf_tear_down(self):
        file_path = "./test.tfrecord"
        os.remove(file_path)
        dir_path = "./tmp/"
        shutil.rmtree(dir_path)

    def generate_random_str(self):
        return ''.join(random.choice(string.ascii_lowercase) for i in range(5))
    
    def test_echo(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = ECHO.format(communication_type=ETL_COMM_HPULL)
        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        # Compare image content
        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()
        self.assertEqual(self.dest_bck.object(self.test_image_filename).get().read_all(), original_image_content)

        # Compare text content
        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()
        self.assertEqual(self.dest_bck.object(self.test_text_filename).get().read_all().decode('utf-8'), original_text_content)


    def test_echo_go(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = GO_ECHO.format(communication_type=ETL_COMM_HPULL)
        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)

        # Wait for the job to finish
        self.client.job(job_id=job_id).wait(verbose=False)

        # Compare image content
        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()
        self.assertEqual(self.dest_bck.object(self.test_image_filename).get().read_all(), original_image_content)

        # Compare text content
        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()
        self.assertEqual(self.dest_bck.object(self.test_text_filename).get().read_all().decode('utf-8'), original_text_content)

    def test_hello_world(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = HELLO_WORLD.format(communication_type=ETL_COMM_HPULL)
        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        # Compare file contents
        self.assertEqual(b"Hello World!", self.dest_bck.object(self.test_text_filename).get().read_all())
        self.assertEqual(b"Hello World!", self.dest_bck.object(self.test_image_filename).get().read_all())

    def test_md5(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = MD5.format(communication_type=ETL_COMM_HPULL)
        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        # Compare image content
        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()    
        md5 = hashlib.md5()
        md5.update(original_image_content)
        hash = md5.hexdigest()
        self.assertEqual(self.dest_bck.object(self.test_image_filename).get().read_all().decode('utf-8'), hash)

        # Compare text content
        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()
        md5 = hashlib.md5()
        md5.update(original_text_content.encode('utf-8'))
        hash = md5.hexdigest()
        self.assertEqual(self.dest_bck.object(self.test_text_filename).get().read_all().decode('utf-8'), hash)

    def test_tar2tf_simple(self):
        self.src_bck.object(self.test_tar_filename).put_file(self.test_tar_source)

        template = TAR2TF.format(communication_type=ETL_COMM_HREV, key="", value="")
        self.test_etl.init_spec(communication_type=ETL_COMM_HREV, template=template)

        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, ext={'tar':'tfrecord'}, to_bck=self.dest_bck)
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        tfrecord_bytes = self.dest_bck.object(self.test_tfrecord_filename).get().read_all()

        tfrecord_filename = "test.tfrecord" 
        with open(tfrecord_filename, 'wb') as f:
            f.write(tfrecord_bytes)

        tfrecord = next(iter(tf.data.TFRecordDataset([tfrecord_filename])))

        example = tf.train.Example()
        example.ParseFromString(tfrecord.numpy())

        cls = example.features.feature['cls'].bytes_list.value[0]
        cls = cls.decode('utf-8')

        transformed_img = example.features.feature['png'].bytes_list.value[0]
        transformed_img = tf.image.decode_image(transformed_img) 

        with tarfile.open(self.test_tar_source, 'r') as tar:
            tar.extractall(path='./tmp')

        original_img = Image.open('./tmp/tar-single/0001.png')
        original_img_tensor = tf.convert_to_tensor(np.array(original_img))
        with open('./tmp/tar-single/0001.cls', 'r') as file:
            original_cls = file.read().strip()

        self.assertTrue(np.array_equal(transformed_img.numpy(), original_img_tensor.numpy()))
        self.assertEqual(cls, original_cls)

        self.tar2tf_tear_down()

    def test_tar2tf_rotation(self):
        self.src_bck.object(self.test_tar_filename).put_file(self.test_tar_source)

        spec = {
            "conversions": [
                {"type": "Decode", "ext_name": "png"},
                {"type": "Rotate", "ext_name": "png", "angle": 30}
            ],
            "selections": [
                {"ext_name": "png"},
                {"ext_name": "cls"}
            ]
        }
        spec = json.dumps(spec)
        template = TAR2TF.format(communication_type=ETL_COMM_HREV, key="-spec", value=spec)
        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HREV)

        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, ext={'tar': 'tfrecord'}, to_bck=self.dest_bck)
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        tfrecord_bytes = self.dest_bck.object(self.test_tfrecord_filename).get().read_all()

        tfrecord_filename = "test.tfrecord"
        with open(tfrecord_filename, 'wb') as f:
            f.write(tfrecord_bytes)

        tfrecord = tf.data.TFRecordDataset([tfrecord_filename])

        raw_record = next(iter(tfrecord))
        example = tf.train.Example()
        example.ParseFromString(raw_record.numpy())

        cls = example.features.feature['cls'].bytes_list.value[0]
        cls = cls.decode('utf-8')

        transformed_img = example.features.feature['png'].bytes_list.value[0]
        transformed_img = tf.image.decode_image(transformed_img)

        with tarfile.open(self.test_tar_source, 'r') as tar:
            tar.extractall(path='./tmp')

        original_img = Image.open('./tmp/tar-single/0001.png').rotate(angle=30, expand=True, fillcolor=(0, 0, 0))
        original_img_tensor = tf.convert_to_tensor(np.array(original_img))
        with open('./tmp/tar-single/0001.cls', 'r') as file:
            original_cls = file.read().strip()

        # Ensure both images have the same dimensions
        transformed_img = tf.image.resize(transformed_img, original_img_tensor.shape[:2])

        # Calculate the SSIM
        score, _ = ssim(transformed_img.numpy(), original_img_tensor.numpy(), full=True, multichannel=True, win_size=3, data_range=255)

        # Assuming we consider images with SSIM > 0.99 as visually identical
        self.assertTrue(score > 0.99)
        self.assertEqual(cls, original_cls)

        self.tar2tf_tear_down()


if __name__ == '__main__':
    unittest.main()
