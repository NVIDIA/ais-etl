#
# Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
#

import os, io, tarfile, json

import tensorflow as tf

from humanfriendly import parse_size
from inspect import isgeneratorfunction
from queue import Queue

from .messages import TargetMsg
from aistore.client.api import Client
from aistore.client import Bck
from .tarutils import tar_records
from .ops import Select, CONVERSIONS, SELECTIONS
from .downloadworker import TarsDownloadWorker

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

OUTPUT_SHAPES = "output_shapes"
OUTPUT_TYPES = "output_types"
MAX_SHARD_SIZE = "max_shard_size"
PATH = "path"
NUM_WORKERS = "num_workers"
RECORD_TO_EXAMPLE = "record_to_example"

tar2tfSpecTemplate = """
apiVersion: v1
kind: Pod
metadata:
  name: tar2tf
  annotations:
    communication_type: "hpull://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistore/tar2tf:latest
      imagePullPolicy: IfNotPresent
      command: ['/go/tar2tf/tar2tf', '-l', '0.0.0.0', '-p', '80', '-spec', '{}']
      ports:
        - name: default
          containerPort: 80
      readinessProbe:
        httpGet:
          path: /health
          port: default
"""


def __bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy()
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def __int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint."""
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


# pylint: disable=unused-variable
def default_record_parser(record):
    keys_to_features = __default_image_desc()
    parsed = tf.io.parse_single_example(record, keys_to_features)

    img = tf.image.decode_jpeg(parsed["image_raw"])
    img = tf.cast(img, float)
    img = tf.image.resize(img, (224, 224))
    img = tf.reshape(img, shape=[224, 224, 3])
    label = tf.cast(parsed["label"], tf.int32)

    return img, label


def __default_image_desc():
    return {
        "height": tf.io.FixedLenFeature([], tf.int64),
        "width": tf.io.FixedLenFeature([], tf.int64),
        "depth": tf.io.FixedLenFeature([], tf.int64),
        "label": tf.io.FixedLenFeature([], tf.int64),
        "image_raw": tf.io.FixedLenFeature([], tf.string),
    }


def default_record_to_pair(record):
    img = tf.image.convert_image_dtype(
        tf.io.decode_jpeg(record["jpg"]), tf.float32
    )
    img = tf.image.resize(img, (224, 224))
    return img, record["cls"]


# Create a dictionary with features that may be relevant.
# this is description of serialization for protobuf
def default_record_to_example(record):
    label = int(record["cls"])
    img = tf.image.decode_jpeg(record["jpg"])

    feature_dict = {
        "height": __int64_feature(img.shape[0]),
        "width": __int64_feature(img.shape[1]),
        "depth": __int64_feature(img.shape[2]),
        "label": __int64_feature(label),
        "image_raw": __bytes_feature(record["jpg"]),
    }

    features = tf.train.Features(feature=feature_dict)
    return tf.train.Example(features=features)


def validate_conversions(convs):
    if type(convs) == list:
        for i in range(len(convs)):
            convs[i] = validate_conversion(convs[i])

        return convs

    convs = validate_conversion(convs)
    return [convs]


def validate_conversion(conv):
    unknown_type_ex = Exception(
        "unknown conversion type. Expected one of {}".format(CONVERSIONS)
    )

    if type(conv) not in CONVERSIONS:
        raise unknown_type_ex

    return conv


def validate_selections(selections):
    if type(selections) != list or len(selections) != 2:
        raise Exception("expected list of length 2")

    selections[0] = validate_selection(selections[0])
    selections[1] = validate_selection(selections[1])

    return selections


def validate_selection(selection):
    unknown_type_ex = Exception(
        "unknown selection type. Expected one of {}".format(SELECTIONS)
    )

    if type(selection) == str:
        return Select(selection)

    if type(selection) not in SELECTIONS:
        raise unknown_type_ex

    return selection


# pylint: disable=unused-variable
class Dataset:
    # pylint: disable=dangerous-default-value
    def __init__(
        self,
        bck: Bck,
        proxy_url="http://localhost:8080",
        conversions=[],
        selections=[],
        remote_exec=None,
    ):
        self.proxy_url = proxy_url
        self.proxy_client = Client(self.proxy_url)
        self.bucket = bck
        self.conversions = validate_conversions(conversions)
        self.selections = validate_selections(selections)
        self.transform_id = ""

        conv_remote_supported = all(
            [c.on_target_allowed() for c in self.conversions]
        )
        sel_remote_supported = all(
            [c.on_target_allowed() for c in self.selections]
        )
        remote_supported = conv_remote_supported and sel_remote_supported

        if remote_exec is None:
            #  User didn't specify remote_exec, use it when possible.
            self.exec_on_target = remote_supported
        elif remote_exec is False:
            self.exec_on_target = False
        else:
            if not conv_remote_supported:
                raise Exception(
                    "given conversions don't support remote execution"
                )
            if not sel_remote_supported:
                raise Exception(
                    "givens selections don't support remote execution"
                )
            self.exec_on_target = True

        if self.exec_on_target:
            msg = TargetMsg(self.conversions, self.selections)
            self.transform_id = self.proxy_client.etl_init(
                tar2tfSpecTemplate.format(json.dumps(dict(msg)))
            )
            print(
                "REMOTE EXECUTION ENABLED, uuid {}".format(self.transform_id)
            )
        else:
            print("REMOTE EXECUTION DISABLED")

    def __get_object_names(self, template):
        smap = self.proxy_client.get_cluster_info()

        # TODO: get all of them directly from proxy
        for t in smap["tmap"]:
            url = smap["tmap"][t]["intra_data_net"]["direct_url"]
            for o in self.proxy_client.get_objects_names(
                self.bucket, url, template
            ):
                yield o

    # args:
    # record_to_pair - specify how to translate tar record to pair
    # path - place to save TFRecord file. If None, everything done on the fly
    def load(self, template, **kwargs):
        accepted_args = [
            OUTPUT_TYPES,
            OUTPUT_SHAPES,
            PATH,
            MAX_SHARD_SIZE,
            NUM_WORKERS,
            RECORD_TO_EXAMPLE,
        ]

        for key in kwargs:
            if key not in accepted_args:
                raise Exception("invalid argument name {}".format(key))

        output_types = kwargs.get(OUTPUT_TYPES, (tf.float32, tf.int32))
        output_shapes = kwargs.get(
            OUTPUT_SHAPES, (tf.TensorShape([224, 224, 3]), tf.TensorShape([]))
        )
        max_shard_size = kwargs.get(MAX_SHARD_SIZE, 0)
        path = kwargs.get(PATH, None)
        num_workers = kwargs.get(NUM_WORKERS, 4)
        record_parser = kwargs.get(
            RECORD_TO_EXAMPLE, default_record_to_example
        )

        # max_shard_size validation
        if type(max_shard_size) == str:
            max_shard_size = parse_size(max_shard_size)
        elif type(max_shard_size) != int:
            raise Exception(
                "{} can be either string or int".format(MAX_SHARD_SIZE)
            )
        if max_shard_size != 0 and path is None:
            raise Exception(
                "{} not supported without {} argument".format(
                    MAX_SHARD_SIZE, PATH
                )
            )

        # path validation
        if path is not None:
            path_gen = path
            # allow path generators so user can put some more logic to path selection
            if not isgeneratorfunction(path) and type(path) != str:
                raise Exception(
                    "path argument has to be either string or generator"
                )
            if type(path) == str:
                path_gen = lambda: self.__default_path_generator(path)

            return self.__record_dataset_from_tar(
                template, path_gen, record_parser, max_shard_size, num_workers
            )

        if self.exec_on_target:
            return self.__dataset_from_transformer(template, record_parser)

        return tf.data.Dataset.from_generator(
            lambda: self.__samples_local_generator_from_tar(
                template, num_workers
            ),
            output_types,
            output_shapes=output_shapes,
        )

    def stop(self):
        if self.transform_id != "":
            self.proxy_client.etl_stop(self.transform_id)

    def __dataset_from_transformer(self, template, record_parser):
        self.__set_s3_os_vars()
        obj_names = []
        for o in self.__get_object_names(template):
            obj_names.append(
                "s3://{}/{}?uuid={}".format(self.bucket, o, self.transform_id)
            )

        return tf.data.TFRecordDataset(filenames=obj_names).map(record_parser)

    # path - path where to save record dataset
    def __record_dataset_from_tar(
        self,
        template,
        get_path_gen,
        record_to_example,
        max_shard_size,
        num_workers,
    ):
        path_gen = get_path_gen()
        paths = [next(path_gen)]
        writer = tf.io.TFRecordWriter(paths[0])
        total_size = 0

        for tar_obj in self.__objects_local_generator(template, num_workers):
            tar_bytes = io.BytesIO(tar_obj)
            tar = tarfile.open(mode="r", fileobj=tar_bytes)
            records = tar_records(tar)

            for k in records:
                record = records[k]
                tf_example = record_to_example(record)

                serialized = tf_example.SerializeToString()
                writer.write(serialized)
                total_size += len(serialized)
                if total_size > max_shard_size > 0:
                    writer.close()
                    total_size = 0
                    paths.append(next(path_gen))
                    writer = tf.io.TFRecordWriter(paths[-1])

            tar.close()

        writer.close()
        return paths

    def __samples_local_generator_from_tar(self, template, num_workers):
        for obj in self.__objects_local_generator(template, num_workers):
            tar_bytes = io.BytesIO(obj)
            tar = tarfile.open(mode="r", fileobj=tar_bytes)
            records = tar_records(tar)
            for k in records:
                yield self.__select_from_record(
                    self.__convert_record(records[k])
                )

            tar.close()

    # yields uncompressed bytes for each TAR file from template
    def __objects_local_generator(self, template, num_workers):
        smap = self.proxy_client.get_cluster_info()
        if len(smap["tmap"]) == 0:
            yield from ()
            return

        targets_queue = Queue()
        results_queue = Queue(
            num_workers + 1
        )  # question: how much tars do we want to prefetch?
        # each worker will fetch tars from one target
        for k in smap["tmap"]:
            targets_queue.put(smap["tmap"][k])

        for i in range(num_workers):
            worker = TarsDownloadWorker(
                self.proxy_url,
                self.bucket,
                template,
                targets_queue,
                results_queue,
            )
            worker.daemon = True  # detach from main process
            worker.start()

        done_cnt = 0
        while True:
            tar_bytes = results_queue.get()
            if tar_bytes is None:
                done_cnt += 1
                if done_cnt == num_workers:
                    # all workers have finished and all messages have been read
                    break
            else:
                yield tar_bytes

        targets_queue.join()  # should be immediate as we know that workers have finished

    def __convert_record(self, record):
        for c in self.conversions:
            record = c.do(record)

        return record

    def __select_from_record(self, record):
        return self.selections[0].select(record), self.selections[1].select(
            record
        )

    def __set_s3_os_vars(self):
        os.environ["AWS_ACCESS_KEY_ID"] = "key-id"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "access-key"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["S3_ENDPOINT"] = "{}/s3/".format(self.proxy_url)
        os.environ["S3_USE_HTTPS"] = "0"
        os.environ["S3_VERIFY_SSL"] = "0"

        # If TF S3 client doesn't get Content-Length from HEAD request,
        # it starts downloading TFRecords in 178 byte chunks (!!!).
        # Here, just disable downloading in chunks and do everything in one shot.
        os.environ["S3_DISABLE_MULTI_PART_DOWNLOAD"] = "1"

    def __default_path_generator(self, path):
        if "{}" in path:
            path_template = path
            yield path_template.format(0)
        else:
            path_template = "{}" + path
            yield path

        i = 1
        while True:
            yield path_template.format(i)
            i += 1
