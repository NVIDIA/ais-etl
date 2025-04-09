#
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import logging
from io import BytesIO
from typing import Optional

import soundfile as sf

from aistore.sdk.etl.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH
from aistore.sdk.etl import ETLConfig

from tests.utils import (
    format_image_tag_for_git_test_mode,
    cases,
    generate_random_string,
)
from tests.base import TestBase

# Configure logging for the tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

POD_SPEC = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-audio-splitter
  annotations:
    wait_timeout: 10m
    communication_type: "{communication_type}://"
spec:
  containers:
    - name: server
      image: aistorage/transformer_audio_splitter:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 80
      command: ['/code/server.py', '--listen', '0.0.0.0', '--port', '80']
      readinessProbe:
        httpGet:
          path: /health
          port: default
"""


class TestAudioSplitTransformer(TestBase):
    """Unit tests for AIStore Audio Split ETL transformation."""

    def setUp(self):
        """Set up test files and upload them to the AIStore bucket."""
        super().setUp()
        self.test_file_name = "test-audio.wav"
        self.test_file_source = "./resources/test-audio-wav.wav"
        logging.info(
            "Uploading test file '%s' from '%s'",
            self.test_file_name,
            self.test_file_source,
        )
        self.test_bck.object(self.test_file_name).get_writer().put_file(
            self.test_file_source
        )

    def trim_audio(
        self, audio_bytes: bytes, audio_format: str, start_time: float, end_time: float
    ) -> Optional[bytes]:
        """Trim audio bytes from start_time to end_time."""
        logging.info(
            "Trimming audio from %.2f to %.2f seconds in %s format",
            start_time,
            end_time,
            audio_format,
        )
        audio_buffer = BytesIO(audio_bytes)
        with sf.SoundFile(audio_buffer, mode="r") as audio_file:
            sample_rate = audio_file.samplerate
            channels = audio_file.channels
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)
            audio_file.seek(start_sample)
            trimmed_data = audio_file.read(end_sample - start_sample)
        trimmed_audio_buffer = BytesIO()
        with sf.SoundFile(
            trimmed_audio_buffer,
            mode="w",
            samplerate=sample_rate,
            channels=channels,
            format=audio_format,
        ) as trimmed_file:
            trimmed_file.write(trimmed_data)
        trimmed_bytes = trimmed_audio_buffer.getvalue()
        logging.info(
            "Completed trimming audio; output size: %d bytes", len(trimmed_bytes)
        )
        return trimmed_bytes

    def compare_transformed_data_with_local(
        self, filename: str, original_filepath: str, etl_name: str
    ):
        """
        Fetch the transformed file and compare it against the expected trimmed audio.

        Args:
            filename (str): Name of the transformed file.
            original_filepath (str): Path to the original file.
            etl_name (str): Name of the ETL job.
        """
        from_time = "1.00"
        to_time = "2.00"
        logging.info(
            "Fetching transformed data for file '%s' using ETL job '%s'",
            filename,
            etl_name,
        )
        transformed_data_bytes = (
            self.test_bck.object(filename)
            .get_reader(
                etl=ETLConfig(
                    etl_name, args={"from_time": from_time, "to_time": to_time}
                )
            )
            .read_all()
        )
        logging.info("Reading original file from '%s'", original_filepath)
        with open(original_filepath, "rb") as f:
            original_file_bytes = f.read()
        logging.info(
            "Trimming original audio between %s and %s seconds", from_time, to_time
        )
        original_audio_split = self.trim_audio(
            original_file_bytes, "wav", float(from_time), float(to_time)
        )
        logging.info("Comparing transformed audio data with locally trimmed audio")
        self.assertEqual(transformed_data_bytes, original_audio_split)
        logging.info(
            "Audio split transformation comparison succeeded for file '%s'", filename
        )

    def run_audio_split_test(self, communication_type: str):
        """
        Run an Audio Split transformation test using a specified communication type.

        Args:
            communication_type (str): The ETL communication type (HPULL, HPUSH).
        """
        etl_name = f"audio-split-transformer-{generate_random_string(5)}"
        self.etls.append(etl_name)
        logging.info(
            "Starting audio split test with ETL '%s' using communication type '%s'",
            etl_name,
            communication_type,
        )

        template = POD_SPEC.format(communication_type=communication_type)
        if self.git_test_mode == "true":
            logging.info("Git test mode enabled; updating image tag for pod spec")
            template = format_image_tag_for_git_test_mode(template, "audio_splitter")

        logging.info("Initializing ETL transformation with spec:\n%s", template)
        self.client.etl(etl_name).init_spec(
            template=template, communication_type=communication_type
        )

        logging.info(
            "Running transformed data comparison for file '%s'", self.test_file_name
        )
        self.compare_transformed_data_with_local(
            self.test_file_name, self.test_file_source, etl_name
        )

    @cases(ETL_COMM_HPULL, ETL_COMM_HPUSH)
    def test_audio_split_transform(self, communication_type: str):
        """Run the Audio Split ETL transformation for different communication types."""
        logging.info(
            "Starting test for audio split transformation with communication type: %s",
            communication_type,
        )
        self.run_audio_split_test(communication_type)
