"""
Pytest suite for the FFmpeg Transformer.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
from pathlib import Path
from typing import Dict
import io
import random

import soundfile as sf

import pytest
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket, Client
from aistore.sdk.errors import ErrBckNotFound

from tests.const import (
    FFMPEG_TEMPLATE,
    INLINE_PARAM_COMBINATIONS,
    PARAM_COMBINATIONS,
    LABEL_FMT,
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


def _assert_transformed_file(
    out_bytes: bytes,
    orig_bytes: bytes,
    filename: str,
    etl_name: str,
    *,
    max_duration_diff: float = 0.05,
):
    # extract metadata
    out_frames, out_ch, out_sr = _get_audio_meta_from_bytes(out_bytes)
    orig_frames, _, orig_sr = _get_audio_meta_from_bytes(orig_bytes)

    # 1) check channel count
    assert out_ch == 1, (
        f"ETL {etl_name} did not convert {filename} to mono " f"(got {out_ch} channels)"
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


# pylint: disable=too-many-locals
def _verify_test_files(
    test_bck: Bucket,
    local_files: Dict[str, Path],
    etl_name: str,
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

        _assert_transformed_file(out_bytes, orig_bytes, filename, etl_name)


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


# pylint: disable=too-many-arguments, too-many-locals
@pytest.mark.stress
@pytest.mark.parametrize(
    "server_type, comm_type, use_fqn, direct_put", PARAM_COMBINATIONS
)
def test_ffmpeg_stress(
    stress_client: Client,
    stress_audio_bucket: Bucket,
    test_bck: Bucket,
    etl_factory,
    stress_metrics,
    server_type: str,
    comm_type: str,
    use_fqn: bool,
    direct_put: str,
):
    """
    Stress test for Hello-World ETL: copy 10k objects with transformation.
    """
    # Check if bucket exists
    try:
        stress_audio_bucket.head()
    except ErrBckNotFound:
        pytest.skip(f"Skipping test: bucket {stress_audio_bucket.name} does not exist")
    # Initialize ETL
    label = LABEL_FMT.format(
        name="FFMPEG",
        server=server_type,
        comm=comm_type,
        arg="fqn" if use_fqn else "",
        direct=direct_put,
    )
    etl_name = etl_factory(
        tag="ffmpeg",
        server_type=server_type,
        template=FFMPEG_TEMPLATE,
        communication_type=comm_type,
        use_fqn=use_fqn,
        direct_put=direct_put,
    )

    # 2) Run transform job
    job_id = stress_audio_bucket.transform(
        etl_name=etl_name,
        to_bck=test_bck,
        num_workers=24,
        timeout="10m",
        ext={"flac": "wav"},
    )
    job = stress_client.job(job_id)
    job.wait(timeout=600)
    duration = job.get_total_time()
    actual_workers = job.get_details().get_num_workers()
    assert (
        actual_workers == 24
    ), f"Num workers mismatch for copy job - {job_id} (expected: 24, actual: {actual_workers})"

    logger.info("%s %s", label, duration)

    # Cant verify the count as there are files with different extensions

    objs = list(test_bck.list_all_objects())
    orig_objs = list(stress_audio_bucket.list_all_objects())
    assert len(objs) == len(orig_objs), (
        f"ETL {etl_name} did not transform all objects: "
        f"{len(objs)} v.s. {len(orig_objs)}"
    )
    # 4) Sample and verify payload
    samples = random.sample(objs, 20)
    for entry in samples:
        if not entry.name.endswith(".wav"):
            logger.debug("Skipping transformed file %s (not a WAV file)", entry.name)
            continue
        transformed_data = test_bck.object(entry.name).get_reader().read_all()
        orig_data = (
            stress_audio_bucket.object(entry.name.replace("wav", "flac"))
            .get_reader()
            .read_all()
        )
        _assert_transformed_file(transformed_data, orig_data, entry.name, etl_name)

    # Record metric
    stress_metrics.append((label, duration))
