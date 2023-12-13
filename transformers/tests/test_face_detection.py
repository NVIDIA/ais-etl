#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring
import logging

from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
import cv2

# from aistore.sdk.etl_templates import FACE_DETECTION_TRANSFORMER
from tests.utils import git_test_mode_format_image_tag_test
from tests.base import TestBase

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# TODO: move var to aistore.sdk.etl_templates after merge
FACE_DETECTION_TRANSFORMER = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-face-detection
  annotations:
    communication_type: "{communication_type}://"
    wait_timeout: 5m
spec:
  containers:
    - name: server
      image: aistorage/transformer_face_detection:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 8000
      command:  ["gunicorn", "main:app", "--workers", "20", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: FORMAT
          value: "{format}"
        - name: ARG_TYPE
          value: "{arg_type}"
      volumeMounts:
        - name: ais
          mountPath: /tmp/ais
  volumes:
    - name: ais
      hostPath:
        path: /tmp/ais
        type: Directory
"""


class TestTransformers(TestBase):
    def setUp(self):
        super().setUp()
        self.test_image_filename = "test-face-detection.png"
        self.test_image_source = "./resources/test-face-detection.png"
        self.test_bck.object(self.test_image_filename).put_file(self.test_image_source)
        self.cv_net = cv2.dnn.readNetFromCaffe(
            "./../face_detection/model/architecture.txt",
            "./../face_detection/model/weights.caffemodel",
        )

    def get_transformed_image_local(self) -> bytes:
        # transformed image - local
        image = cv2.imread(self.test_image_source)
        image_height, image_width, _ = image.shape
        output_image = image.copy()
        preprocessed_image = cv2.dnn.blobFromImage(
            image,
            scalefactor=1.0,
            size=(300, 300),
            mean=(104.0, 117.0, 123.0),
            swapRB=False,
            crop=False,
        )
        self.cv_net.setInput(preprocessed_image)
        results = self.cv_net.forward()

        for face in results[0][0]:
            face_confidence = face[2]
            if face_confidence > 0.6:
                bbox = face[3:]
                x_1 = int(bbox[0] * image_width)
                y_1 = int(bbox[1] * image_height)
                x_2 = int(bbox[2] * image_width)
                y_2 = int(bbox[3] * image_height)
                cv2.rectangle(
                    output_image,
                    pt1=(x_1, y_1),
                    pt2=(x_2, y_2),
                    color=(0, 255, 0),
                    thickness=image_width // 200,
                )
        _, encoded_image = cv2.imencode(".png", output_image)
        return encoded_image.tobytes()

    def get_template(self, comm_type: str, arg_type: str) -> str:
        template = FACE_DETECTION_TRANSFORMER.format(
            communication_type=comm_type,
            format="png",
            arg_type=arg_type,
        )
        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "face_detection")
        return template

    def run_face_detection_test(self, communication_type: str, fqn_flag: bool = False):
        arg_type = "fqn" if fqn_flag else ""
        template = self.get_template(communication_type, arg_type)
        self.test_etl.init_spec(
            template=template,
            communication_type=communication_type,
            arg_type=arg_type,
            timeout="10m",
        )

        logger.info(self.test_etl.view())

        transformed_image_etl = (
            self.test_bck.object(self.test_image_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )
        self.assertEqual(self.get_transformed_image_local(), transformed_image_etl)

    def test_face_detection_transformer_hpull(self):
        self.run_face_detection_test(communication_type=ETL_COMM_HPULL, fqn_flag=False)

    def test_face_detection_transformer_hrev(self):
        self.run_face_detection_test(communication_type=ETL_COMM_HREV, fqn_flag=False)

    def test_face_detection_transformer_hpush(self):
        self.run_face_detection_test(communication_type=ETL_COMM_HPUSH, fqn_flag=False)

    def test_face_detection_transformer_hpush_fqn(self):
        self.run_face_detection_test(communication_type=ETL_COMM_HPUSH, fqn_flag=True)

    def test_face_detection_transformer_hpull_fqn(self):
        self.run_face_detection_test(communication_type=ETL_COMM_HPULL, fqn_flag=True)
