#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#

import json
import os

import ffmpeg

from aistore.sdk.etl_const import ETL_COMM_HPULL, ETL_COMM_HPUSH, ETL_COMM_HREV
from aistore.sdk.etl_templates import FFMPEG

from tests.base import TestBase
from tests.utils import git_test_mode_format_image_tag_test


class TestFFMPEGTransformer(TestBase):
    def decode_data(self, data, **kwargs):
        input_stream = ffmpeg.input("pipe:0")
        output_stream = ffmpeg.output(input_stream, "pipe:1", **kwargs)
        out, _ = ffmpeg.run(
            output_stream, input=data, capture_stdout=True, capture_stderr=True
        )
        return out

    def test_ffmpeg_from_wav_to_flac_hpull(self):
        self.run_ffmpeg_test(
            ETL_COMM_HPULL,
            "test-audio-wav.wav",
            "./resources/test-audio-wav.wav",
            {"format": "flac", "ar": 48000, "ac": 2},
        )

    def test_ffmpeg_from_mp3_to_wav_hpull(self):
        self.run_ffmpeg_test(
            ETL_COMM_HPULL,
            "test-audio-mp3.mp3",
            "./resources/test-audio-mp3.mp3",
            {"format": "wav", "ar": 44100, "ac": 2, "af": "loudnorm"},
        )

    def test_ffmpeg_format_autodetection_hpull(self):
        test_filename = "test-audio-wav.wav"
        test_source = "./resources/test-audio-wav.wav"
        _, extension = os.path.splitext(test_filename)
        file_format = extension[1:]

        self.run_ffmpeg_test(
            ETL_COMM_HPULL,
            test_filename,
            test_source,
            {"acodec": "pcm_s16le"},
            autodetect_format=file_format,
        )

    def test_ffmpeg_from_wav_to_flac_hpush(self):
        self.run_ffmpeg_test(
            ETL_COMM_HPUSH,
            "test-audio-wav.wav",
            "./resources/test-audio-wav.wav",
            {"format": "flac", "ar": 48000, "ac": 2},
        )

    def test_ffmpeg_from_mp3_to_wav_hpush(self):
        self.run_ffmpeg_test(
            ETL_COMM_HPUSH,
            "test-audio-mp3.mp3",
            "./resources/test-audio-mp3.mp3",
            {"format": "wav", "ar": 44100, "ac": 2, "af": "loudnorm"},
        )

    def test_ffmpeg_format_autodetection_hpush(self):
        test_filename = "test-audio-wav.wav"
        test_source = "./resources/test-audio-wav.wav"
        _, extension = os.path.splitext(test_filename)
        file_format = extension[1:]

        self.run_ffmpeg_test(
            ETL_COMM_HPUSH,
            test_filename,
            test_source,
            {"acodec": "pcm_s16le"},
            autodetect_format=file_format,
        )

    def test_ffmpeg_from_wav_to_flac_hrev(self):
        self.run_ffmpeg_test(
            ETL_COMM_HREV,
            "test-audio-wav.wav",
            "./resources/test-audio-wav.wav",
            {"format": "flac", "ar": 48000, "ac": 2},
        )

    def test_ffmpeg_from_mp3_to_wav_hrev(self):
        self.run_ffmpeg_test(
            ETL_COMM_HREV,
            "test-audio-mp3.mp3",
            "./resources/test-audio-mp3.mp3",
            {"format": "wav", "ar": 44100, "ac": 2, "af": "loudnorm"},
        )

    def test_ffmpeg_format_autodetection_hrev(self):
        test_filename = "test-audio-wav.wav"
        test_source = "./resources/test-audio-wav.wav"
        _, extension = os.path.splitext(test_filename)
        file_format = extension[1:]

        self.run_ffmpeg_test(
            ETL_COMM_HREV,
            test_filename,
            test_source,
            {"acodec": "pcm_s16le"},
            autodetect_format=file_format,
        )

    # pylint: disable=too-many-arguments
    def run_ffmpeg_test(
        self,
        communication_type,
        test_filename,
        test_source,
        ffmpeg_options,
        autodetect_format=None,
    ):
        self.test_bck.object(test_filename).put_file(test_source)

        if autodetect_format is not None:
            ffmpeg_options["format"] = autodetect_format

        template = FFMPEG.format(
            communication_type=communication_type,
            ffmpeg_options=json.dumps(ffmpeg_options),
        )

        if self.git_test_mode == "true":
            template = git_test_mode_format_image_tag_test(template, "ffmpeg")

        self.test_etl.init_spec(
            template=template, communication_type=communication_type
        )
        etl_transformed_content = (
            self.test_bck.object(test_filename)
            .get(etl_name=self.test_etl.name)
            .read_all()
        )

        with open(test_source, "rb") as file:
            original_audio_content = file.read()
            local_transformed_content = self.decode_data(
                original_audio_content, **ffmpeg_options
            )

        self.assertEqual(local_transformed_content, etl_transformed_content)
