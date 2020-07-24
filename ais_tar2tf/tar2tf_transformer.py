#
# Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
#

# This is a code snippet which starts tar2tf transformer
# and makes it possible to on-the-fly transform TAR files to
# TFRecords using TensorFlow's tf.data.TFRecordDataset("s3://bucket/object!uuid).

import requests

tar2tf_spec = '''
apiVersion: v1
kind: Pod
metadata:
  name: tar2tf-test
  annotations:
    communication_type: "hrev://"
    wait_timeout: 2m
spec:
  containers:
    - name: server
      image: aistore/tar2tf:latest
      ports:
        - containerPort: 80

'''

# Returns transform uuid
def init_tar2tf(proxy_url):
    init_url = "{}/v1/transform".format(proxy_url)
    return requests.post(init_url, tar2tf_spec).json()