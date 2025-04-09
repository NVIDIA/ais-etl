#
# Copyright (c) 2023-2025, NVIDIA CORPORATION. All rights reserved.
#

import logging
import cv2

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl.etl_templates import FACE_DETECTION_TRANSFORMER
from aistore.sdk.etl import ETLConfig

from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)
from tests.base import TestBase

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TestFaceDetectionTransformer(TestBase):
    """Unit tests for AIStore ETL Face Detection transformation."""

    def setUp(self):
        """Sets up the test environment by uploading a test image and loading the face detection model."""
        super().setUp()
        self.test_image_filename = "test-face-detection.png"
        self.test_image_source = "./resources/test-face-detection.png"

        # Upload test image to the AIStore bucket
        self.test_bck.object(self.test_image_filename).get_writer().put_file(
            self.test_image_source
        )

        # Load the pre-trained face detection model
        self.cv_net = cv2.dnn.readNetFromCaffe(
            "./../face_detection/model/architecture.txt",
            "./../face_detection/model/weights.caffemodel",
        )

    def get_transformed_image_local(self) -> bytes:
        """
        Applies face detection locally using OpenCV to compare with the AIStore ETL-transformed image.

        Returns:
            bytes: The locally transformed image in PNG format.
        """
        image = cv2.imread(self.test_image_source)
        image_height, image_width, _ = image.shape
        output_image = image.copy()

        # Preprocess the image for face detection
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

        # Draw bounding boxes around detected faces
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

        # Encode the transformed image to PNG format
        _, encoded_image = cv2.imencode(".png", output_image)
        return encoded_image.tobytes()

    def initialize_etl(self, comm_type: str, etl_name: str, arg_type: str):
        """Initializes the ETL transformation with the specified parameters."""
        template = FACE_DETECTION_TRANSFORMER.format(
            communication_type=comm_type,
            format="png",
            arg_type=arg_type,
        )

        # Adjust template for Git test mode
        template = format_image_tag_for_git_test_mode(template, "face_detection")

        # Initialize ETL transformation
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=comm_type, arg_type=arg_type
        )

        logger.info(
            "Initialized ETL: %s\n%s", etl_name, self.client.etl(etl_name).view()
        )

    def run_face_detection_test(self, communication_type: str, fqn_flag: bool = False):
        """
        Runs a face detection transformation test, comparing AIStore ETL output to local transformation.

        Args:
            communication_type (str): The ETL communication type.
            fqn_flag (bool): Whether to use fully qualified names (FQN).
        """
        etl_name = f"face-detect-{generate_random_string(5)}"
        self.etls.append(etl_name)

        arg_type = "fqn" if fqn_flag else ""
        self.initialize_etl(communication_type, etl_name, arg_type)

        logger.info(
            f"Running face detection ETL test with {communication_type} (ETL: {etl_name})"
        )

        # Retrieve transformed image from AIStore ETL
        transformed_image_etl = (
            self.test_bck.object(self.test_image_filename)
            .get_reader(etl=ETLConfig(etl_name))
            .read_all()
        )

        # Compare ETL-transformed image with locally transformed image
        self.assertEqual(self.get_transformed_image_local(), transformed_image_etl)

    @cases(
        (ETL_COMM_HPULL, False),
        (ETL_COMM_HPUSH, False),
        (ETL_COMM_HPUSH, True),
        (ETL_COMM_HPULL, True),
    )
    def test_face_detection_transformer(self, test_case):
        communication_type, fqn_flag = test_case
        """Runs face detection transformation tests for different communication types and FQN settings."""
        self.run_face_detection_test(communication_type, fqn_flag)
