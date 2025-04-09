#
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
#
# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring

import logging
from io import BytesIO

import tarfile
import json
from typing import Optional, Dict, Any

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

AUDIO_SPLIT_SPEC = """
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

AUDIO_MANAGER_SPEC = """
apiVersion: v1
kind: Pod
metadata:
  name: transformer-audio-manager
  annotations:
    # Values it can take ["hpull://","hpush://"]
    communication_type: "hpull://"
    wait_timeout: 10m
spec:
  containers:
    - name: server
      image: aistorage/transformer_audio_manager:latest
      imagePullPolicy: Always
      ports:
        - name: default
          containerPort: 80
      command: ['/code/server.py', '--listen', '0.0.0.0', '--port', '80']
      readinessProbe:
        httpGet:
          path: /health
          port: default
      env:
        - name: AIS_ENDPOINT
          value: "{ais_endpoint}"
        - name: SRC_BUCKET
          value: "{bck_name}"
        - name: SRC_PROVIDER
          value: "ais"  
        - name: OBJ_PREFIX
          value: ""
        - name: OBJ_EXTENSION
          value: "wav"
        - name: ETL_NAME
          value: "{etl_name}"
"""


class TestAudioSplitConsolidate(TestBase):
    """Unit tests for AIStore Audio Manager ETL transformation."""

    def setUp(self):
        """Set up test files and upload them to the AIStore bucket."""
        super().setUp()
        self.test_file_name = "test-audio.wav"
        self.test_file_source = "./resources/test-audio-wav.wav"
        self.test_manifest_name = "test-manifest.jsonl"
        self.test_manifest_source = "./resources/test-manifest.jsonl"

        logging.info(
            "Uploading test file '%s' from '%s'",
            self.test_file_name,
            self.test_file_source,
        )
        self.test_bck.object(self.test_file_name).get_writer().put_file(
            self.test_file_source
        )
        logging.info(
            "Uploading test manifest file '%s' from '%s'",
            self.test_manifest_name,
            self.test_manifest_source,
        )
        self.test_bck.object(self.test_manifest_name).get_writer().put_file(
            self.test_manifest_source
        )

    def fetch_transformed_audio(self, data: dict, split_etl_name: str) -> bytes:
        """Retrieve transformed audio file from AIS using ETL."""
        try:
            audio_id = data.get("id")
            obj_path = f"{audio_id}.wav"

            obj = self.test_bck.object(obj_path)
            return obj.get_reader(
                etl=ETLConfig(name=split_etl_name, args=data), direct=True
            ).read_all()
        except Exception as e:
            logging.exception(
                "Error fetching transformed audio for ID %s: %s", audio_id, str(e)
            )
            raise

    def process_json_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Process a single JSON line and return parsed data."""
        try:
            data = json.loads(line.strip())
            if not all(key in data for key in ("id", "part", "from_time", "to_time")):
                logging.warning("Missing required fields in JSON line: %s", line)
                return None
            return data
        except json.JSONDecodeError as e:
            logging.error("Invalid JSON line: %s - Error: %s", line, e)
            return None

    def create_tar_archive(self, input_bytes: bytes, split_etl_name: str) -> bytes:
        """Create tar archive from JSONL input containing audio processing instructions."""
        output_tar = BytesIO()
        processed_count = 0

        try:
            with tarfile.open(fileobj=output_tar, mode="w") as tar:
                for line_number, line in enumerate(
                    input_bytes.decode().splitlines(), 1
                ):
                    if not line.strip():
                        continue

                    if (data := self.process_json_line(line)) is None:
                        logging.info("Skipping invalid line %d : %s", line_number, line)
                        continue

                    try:
                        audio_content = self.fetch_transformed_audio(
                            data, split_etl_name
                        )
                        tar_info = tarfile.TarInfo(
                            name=f"{data['id']}_{data['part']}.wav"
                        )
                        tar_info.size = len(audio_content)
                        tar.addfile(tar_info, BytesIO(audio_content))
                        processed_count += 1

                    except Exception as e:
                        logging.error("Failed to process line %d: %s", line_number, e)

            logging.info("Created tar archive with %d audio files", processed_count)
            return output_tar.getvalue()
        except Exception as e:
            logging.error("Tar creation failed: %s", e)
            raise

    def compare_transformed_data_with_local(
        self,
        filename: str,
        original_filepath: str,
        manager_etl_name: str,
        split_etl_name: str,
    ):
        """
        Fetch the transformed file and compare it against the expected tar file.

        Args:
            filename (str): Name of the transformed file.
            original_filepath (str): Path to the original file.
            manager_etl_name (str): Name of the Audio Manager ETL.
            split_etl_name (str): Name of the Audio Splitter ETL.
        """
        # Transformed tar bytes
        transformed_tar_bytes = (
            self.test_bck.object(filename)
            .get_reader(etl=ETLConfig(name=manager_etl_name))
            .read_all()
        )

        # Generate expected tar bytes from original manifest
        with open(original_filepath, "rb") as f:
            original_file_bytes = f.read()
        original_tar_bytes = self.create_tar_archive(
            original_file_bytes, split_etl_name
        )

        # Compare tar structure and content
        with tarfile.open(
            fileobj=BytesIO(transformed_tar_bytes), mode="r"
        ) as transformed_tar:
            transformed_files = {
                member.name: transformed_tar.extractfile(member).read()
                for member in transformed_tar.getmembers()
                if member.isfile()
            }

        with tarfile.open(
            fileobj=BytesIO(original_tar_bytes), mode="r"
        ) as original_tar:
            original_files = {
                member.name: original_tar.extractfile(member).read()
                for member in original_tar.getmembers()
                if member.isfile()
            }

        # Validate file count
        self.assertEqual(
            len(transformed_files),
            len(original_files),
            f"File count mismatch: Transformed has {len(transformed_files)}, expected {len(original_files)}",
        )

        # Validate each file's existence and content
        self.assertDictEqual(original_files, transformed_files)

        logging.info(
            "Successfully validated %d files with matching content", len(original_files)
        )

    def run_audio_split_consolidate_test(self, communication_type: str):
        """
        Run an Audio Split Consolidate transformation test using a specified communication type.

        Args:
            communication_type (str): The ETL communication type (HPULL, HPUSH).
        """
        # Create audio splitter ETL
        audio_split_etl_name = f"audio-split-transformer-{generate_random_string(5)}"
        self.etls.append(audio_split_etl_name)
        logging.info(
            "Starting audio split test with ETL '%s' using communication type '%s'",
            audio_split_etl_name,
            communication_type,
        )

        template = AUDIO_SPLIT_SPEC.format(communication_type=communication_type)
        if self.git_test_mode == "true":
            logging.info("Git test mode enabled; updating image tag for pod spec")
            template = format_image_tag_for_git_test_mode(template, "audio_splitter")
        logging.info("Initializing ETL transformation with spec:\n%s", template)
        self.client.etl(audio_split_etl_name).init_spec(
            template=template, communication_type=communication_type
        )

        # Create audio manager ETL
        audio_manager_etl_name = f"audio-manager-{generate_random_string(5)}"
        self.etls.append(audio_manager_etl_name)
        logging.info(
            "Starting audio manager test with ETL '%s' using communication type '%s'",
            audio_manager_etl_name,
            communication_type,
        )
        template = AUDIO_MANAGER_SPEC.format(
            communication_type=communication_type,
            ais_endpoint=self.endpoint,
            bck_name=self.test_bck.name,
            etl_name=audio_split_etl_name,
        )
        if self.git_test_mode == "true":
            logging.info("Git test mode enabled; updating image tag for pod spec")
            template = format_image_tag_for_git_test_mode(template, "audio_manager")
        logging.info("Initializing ETL transformation with spec:\n%s", template)
        self.client.etl(audio_manager_etl_name).init_spec(
            template=template, communication_type=communication_type
        )

        # compare transformed data with local
        logging.info(
            "Running transformed data comparison for file '%s'", self.test_manifest_name
        )
        self.compare_transformed_data_with_local(
            self.test_manifest_name,
            self.test_manifest_source,
            audio_manager_etl_name,
            audio_split_etl_name,
        )

    @cases(ETL_COMM_HPULL, ETL_COMM_HPUSH)
    def test_audio_split_consolidate(self, communication_type: str):
        """Run the Audio Split ETL transformation for different communication types."""
        logging.info(
            "Starting test for audio split consolidate transformer with communication type: %s",
            communication_type,
        )
        self.run_audio_split_consolidate_test(communication_type)
