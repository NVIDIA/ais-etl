"""
Pytest suite for the FFmpeg Transformer.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
from pathlib import Path
from typing import Dict
import io

import soundfile as sf

import pytest
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket

from tests.const import (
    FFMPEG_TEMPLATE,
    INLINE_PARAM_COMBINATIONS,
)

# Configure module-level logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def _get_audio_meta_from_bytes(buf: bytes):
    """
    Return (num_frames, num_channels, sample_rate) for an audio file in any
    libsndfile-supported format (WAV, FLAC, etc.) given as bytes.

    This reads only the header—no need to pull the entire data into RAM.
    """
    bio = io.BytesIO(buf)
    with sf.SoundFile(bio) as f:
        return f.frames, f.channels, f.samplerate


# pylint: disable=too-many-locals
def _verify_test_files(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_name: str,
    *,
    max_duration_diff: float = 0.05,
):
    """
    Verify that each transformed file
      1) is mono (1 channel),
      2) has sample_rate == 44100 Hz,
      3) and duration matches the original within `max_duration_diff` seconds.

    Args:
        test_bck:        the AIS bucket containing the transformed files
        local_files:     map of filename -> local Path to the original
        etl_name:        the ETL job name to use
        max_duration_diff: allowed difference in seconds (default 5 ms)
    """
    for filename, orig_path in local_files.items():
        # read transformed bytes
        reader = test_bck.object(filename).get_reader(etl=ETLConfig(etl_name))
        out_bytes = reader.read_all()

        # read original bytes
        orig_bytes = Path(orig_path).read_bytes()

        # extract metadata
        out_frames, out_ch, out_sr = _get_audio_meta_from_bytes(out_bytes)
        orig_frames, _, orig_sr = _get_audio_meta_from_bytes(orig_bytes)

        # 1) check channel count
        assert out_ch == 1, (
            f"ETL {etl_name} did not convert {filename} to mono "
            f"(got {out_ch} channels)"
        )

        # 2) check sample rate
        assert out_sr == 16000, (
            f"ETL {etl_name} did not convert {filename} to 16 kHz " f"(got {out_sr} Hz)"
        )

        # 3) check duration
        orig_duration = orig_frames / orig_sr
        out_duration = out_frames / out_sr
        diff = abs(orig_duration - out_duration)
        assert diff <= max_duration_diff, (
            f"Duration mismatch for {filename}: "
            f"original={orig_duration:.3f}s, transformed={out_duration:.3f}s, "
            f"diff={diff:.3f}s (allowed {max_duration_diff}s)"
        )


# pylint: disable=too-many-arguments
@pytest.mark.parametrize("server_type, comm_type, use_fqn", INLINE_PARAM_COMBINATIONS)
def test_ffmpeg_transformer(
    test_bck: Bucket,
    local_audio_files: Dict[str, Path],
    etl_factory,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    Validate the Python-based FFmpeg ETL transformer.
    """
    # Upload inputs
    for filename, path in local_audio_files.items():
        test_bck.object(filename).get_writer().put_file(str(path))

    # Build and initialize ETL
    etl_name = etl_factory(
        tag="ffmpeg",
        server_type=server_type,
        template=FFMPEG_TEMPLATE,
        communication_type=comm_type,
        use_fqn=use_fqn,
    )
    logger.info(
        "Initialized Echo ETL '%s' (server=%s, comm=%s, fqn=%s)",
        etl_name,
        server_type,
        comm_type,
        use_fqn,
    )

    _verify_test_files(
        test_bck,
        local_audio_files,
        etl_name,
    )
