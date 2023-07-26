#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import bz2
import gzip
import hashlib
import json
import time
import os
import random
import shutil
import string
import tarfile
import unittest

import yaml

import numpy as np
import tensorflow as tf

from PIL import Image
from skimage.metrics import structural_similarity as ssim

from aistore import Client
from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HREV
from aistore.sdk.etl_templates import GO_ECHO, ECHO, HELLO_WORLD, MD5, TAR2TF, COMPRESS  # TODO: Add COMPRESS once PyPI images are updated

class TestTransformers(unittest.TestCase):
    def setUp(self):
        self.endpoint = os.environ.get("AIS_ENDPOINT", "http://192.168.49.2:8080")
        self.git_test_mode = os.getenv('GIT_TEST', 'False')
        self.client = Client(self.endpoint)
        self.src_bck = self.client.bucket("src").create(exist_ok=True)
        self.dest_bck = self.client.bucket("dest").create(exist_ok=True)

        self.test_image_filename = "test-image.jpg"
        self.test_image_source = "./resources/test-image.jpg"
        self.test_text_filename = "test-text.txt"
        self.test_text_source = "./resources/test-text.txt"
        self.test_tar_filename = "test-tar-single.tar"
        self.test_tar_source = "./resources/test-tar-single.tar"
        self.test_tfrecord_filename = "test-tar-single.tfrecord"
        self.test_image_gz_filename = "test-image.jpg.gz"
        self.test_image_gz_source = "./resources/test-image.jpg.gz"
        self.test_text_gz_filename = "test-text.txt.gz"
        self.test_text_gz_source = "./resources/test-text.txt.gz"
        self.test_image_bz2_filename = "test-image.jpg.bz2"
        self.test_image_bz2_source = "./resources/test-image.jpg.bz2"
        self.test_text_bz2_filename = "test-text.txt.bz2"
        self.test_text_bz2_source = "./resources/test-text.txt.bz2"

        self.test_etl = self.client.etl("test-etl-" + self.generate_random_str()) 

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

    # For Git testing purposes (if $GIT_TEST is True, tests will use image with test tag)
    def __git_test_mode_format_image_tag_test(self, template, img):
        template = yaml.safe_load(template)
        template['spec']['containers'][0]['image'] = f"aistorage/transformer_{img}:test"
        return yaml.dump(template)
    
    # TODO: Remove once etl_templates are updated (imagePullPolicy should be set to Always)
    def __git_test_mode_format_image_pull_policy(self, template):
        template = yaml.safe_load(template)
        template['spec']['containers'][0]['imagePullPolicy'] = "Always"
        return yaml.dump(template)

    def generate_random_str(self):
        return ''.join(random.choice(string.ascii_lowercase) for i in range(5))

    @unittest.skipIf(os.getenv('ECHO_ENABLE', 'true') == 'false', "ECHO is disabled")
    def test_echo(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = ECHO.format(communication_type=ETL_COMM_HPULL)

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "echo")
        
        template = self.__git_test_mode_format_image_pull_policy(template)

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

    @unittest.skipIf(os.getenv('GO_ECHO_ENABLE', 'true') == 'false', "GO_ECHO is disabled")
    def test_echo_go(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = GO_ECHO.format(communication_type=ETL_COMM_HPULL)

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "echo_go")

        template = self.__git_test_mode_format_image_pull_policy(template)

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

    @unittest.skipIf(os.getenv('HELLO_WORLD_ENABLE', 'true') == 'false', "HELLO_WORLD is disabled")
    def test_hello_world(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = HELLO_WORLD.format(communication_type=ETL_COMM_HPULL)

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "hello_world")

        template = self.__git_test_mode_format_image_pull_policy(template)

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)

        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        # Compare file contents
        self.assertEqual(b"Hello World!", self.dest_bck.object(self.test_text_filename).get().read_all())
        self.assertEqual(b"Hello World!", self.dest_bck.object(self.test_image_filename).get().read_all())

    @unittest.skipIf(os.getenv('MD5_ENABLE', 'true') == 'false', "MD5 is disabled")
    def test_md5(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = MD5.format(communication_type=ETL_COMM_HPULL)

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "md5")

        template = self.__git_test_mode_format_image_pull_policy(template)

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
    @unittest.skipIf(os.getenv('TAR2TF_ENABLE', 'true') == 'false', "TAR2TF is disabled")
    def test_tar2tf_simple(self):
        self.src_bck.object(self.test_tar_filename).put_file(self.test_tar_source)

        template = TAR2TF.format(communication_type=ETL_COMM_HREV, arg="", val="")

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "tar2tf")

        template = self.__git_test_mode_format_image_pull_policy(template)

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
    
    @unittest.skipIf(os.getenv('TAR2TF_ENABLE', 'true') == 'false', "TAR2TF is disabled")
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

        template = TAR2TF.format(communication_type=ETL_COMM_HREV, arg="-spec", val=spec)

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "tar2tf")

        template = self.__git_test_mode_format_image_pull_policy(template)

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

    @unittest.skipIf(os.getenv('COMPRESS_ENABLE', 'true') == 'false', "COMPRESS is disabled")
    def test_compress_gzip(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = COMPRESS.format(communication_type=ETL_COMM_HPULL, arg1="--mode", val1="compress", arg2="--compression", val2="gzip")

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "compress")

        template = self.__git_test_mode_format_image_pull_policy(template)

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)
        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)
        # Wait for the job to finish
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        compressed_image = self.dest_bck.object(self.test_image_filename).get().read_all()
        compressed_text = self.dest_bck.object(self.test_text_filename).get().read_all()

        self.assertNotEqual(compressed_image, b"Data processing failed")
        self.assertNotEqual(compressed_text, b"Data processing failed")
        
        # Decompress the files
        decompressed_image = gzip.decompress(compressed_image)
        decompressed_text = gzip.decompress(compressed_text)

        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()
        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()

        self.assertEqual(decompressed_image, original_image_content)
        self.assertEqual(decompressed_text.decode('utf-8'), original_text_content)

        # Calculate the checksums
        original_image_checksum = hashlib.md5(original_image_content).hexdigest()
        decompressed_image_checksum = hashlib.md5(decompressed_image).hexdigest()
        original_text_checksum = hashlib.md5(original_text_content.encode('utf-8')).hexdigest()
        decompressed_text_checksum = hashlib.md5(decompressed_text).hexdigest()

        # Validate the checksums
        self.assertEqual(original_image_checksum, decompressed_image_checksum)
        self.assertEqual(original_text_checksum, decompressed_text_checksum)

    @unittest.skipIf(os.getenv('COMPRESS_ENABLE', 'true') == 'false', "COMPRESS is disabled")
    def test_compress_bz2(self):
        self.src_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.src_bck.object(self.test_text_filename).put_file(self.test_text_source)

        template = COMPRESS.format(communication_type=ETL_COMM_HPULL, arg1="--mode", val1="compress", arg2="--compression", val2="bz2")

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "compress")

        template = self.__git_test_mode_format_image_pull_policy(template)

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)
        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)
        # Wait for the job to finish
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        compressed_image = self.dest_bck.object(self.test_image_filename).get().read_all()
        compressed_text = self.dest_bck.object(self.test_text_filename).get().read_all()

        self.assertNotEqual(compressed_image, b"Data processing failed")
        self.assertNotEqual(compressed_text, b"Data processing failed")

        # Decompress the files
        decompressed_image = bz2.decompress(compressed_image)
        decompressed_text = bz2.decompress(compressed_text)

        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()
        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()
        
        self.assertEqual(decompressed_image, original_image_content)
        self.assertEqual(decompressed_text.decode('utf-8'), original_text_content)

        # Calculate the checksums
        original_image_checksum = hashlib.md5(original_image_content).hexdigest()
        decompressed_image_checksum = hashlib.md5(decompressed_image).hexdigest()
        original_text_checksum = hashlib.md5(original_text_content.encode('utf-8')).hexdigest()
        decompressed_text_checksum = hashlib.md5(decompressed_text).hexdigest()

        # Validate the checksums
        self.assertEqual(original_image_checksum, decompressed_image_checksum)
        self.assertEqual(original_text_checksum, decompressed_text_checksum)

    @unittest.skipIf(os.getenv('COMPRESS_ENABLE', 'true') == 'false', "COMPRESS is disabled")
    def test_decompress_gzip(self):
        self.src_bck.object(self.test_image_gz_filename).put_file(self.test_image_gz_source)
        self.src_bck.object(self.test_text_gz_filename).put_file(self.test_text_gz_source)

        template = COMPRESS.format(communication_type=ETL_COMM_HPULL, arg1="--mode", val1="decompress", arg2="--compression", val2="gzip")

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "compress")

        template = self.__git_test_mode_format_image_pull_policy(template)

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)
        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)
        # Wait for the job to finish
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        decompressed_image = self.dest_bck.object(self.test_image_gz_filename).get().read_all()
        decompressed_text = self.dest_bck.object(self.test_text_gz_filename).get().read_all()

        self.assertNotEqual(decompressed_image, b"Data processing failed")
        self.assertNotEqual(decompressed_image, b"Data processing failed")

        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()
        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()

        self.assertEqual(decompressed_image, original_image_content)
        self.assertEqual(decompressed_text.decode('utf-8'), original_text_content)

        # Calculate the checksums
        original_image_checksum = hashlib.md5(original_image_content).hexdigest()
        decompressed_image_checksum = hashlib.md5(decompressed_image).hexdigest()
        original_text_checksum = hashlib.md5(original_text_content.encode('utf-8')).hexdigest()
        decompressed_text_checksum = hashlib.md5(decompressed_text).hexdigest()

        # Validate the checksums
        self.assertEqual(original_image_checksum, decompressed_image_checksum)
        self.assertEqual(original_text_checksum, decompressed_text_checksum)

    @unittest.skipIf(os.getenv('COMPRESS_ENABLE', 'true') == 'false', "COMPRESS is disabled")
    def test_decompress_bz2(self):
        self.src_bck.object(self.test_image_bz2_filename).put_file(self.test_image_bz2_source)
        self.src_bck.object(self.test_text_bz2_filename).put_file(self.test_text_bz2_source)

        template = COMPRESS.format(communication_type=ETL_COMM_HPULL, arg1="--mode", val1="decompress", arg2="--compression", val2="bz2")

        if self.git_test_mode == 'true':
            template = self.__git_test_mode_format_image_tag_test(template, "compress")

        template = self.__git_test_mode_format_image_pull_policy(template)

        self.test_etl.init_spec(template=template, communication_type=ETL_COMM_HPULL)
        transform_job_id = self.src_bck.transform(etl_name=self.test_etl.name, to_bck=self.dest_bck)
        # Wait for the job to finish
        self.client.job(job_id=transform_job_id).wait(verbose=False)

        decompressed_image = self.dest_bck.object(self.test_image_bz2_filename).get().read_all()
        decompressed_text = self.dest_bck.object(self.test_text_bz2_filename).get().read_all()

        self.assertNotEqual(decompressed_image, b"Data processing failed")
        self.assertNotEqual(decompressed_image, b"Data processing failed")

        with open(self.test_image_source, 'rb') as file:
            original_image_content = file.read()
        with open(self.test_text_source, 'r') as file:
            original_text_content = file.read()

        self.assertEqual(decompressed_image, original_image_content)
        self.assertEqual(decompressed_text.decode('utf-8'), original_text_content)

        # Calculate the checksums
        original_image_checksum = hashlib.md5(original_image_content).hexdigest()
        decompressed_image_checksum = hashlib.md5(decompressed_image).hexdigest()
        original_text_checksum = hashlib.md5(original_text_content.encode('utf-8')).hexdigest()
        decompressed_text_checksum = hashlib.md5(decompressed_text).hexdigest()

        # Validate the checksums
        self.assertEqual(original_image_checksum, decompressed_image_checksum)
        self.assertEqual(original_text_checksum, decompressed_text_checksum)


if __name__ == '__main__':
    unittest.main()
