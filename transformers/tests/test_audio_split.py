"""
Pytest suite for the Audio Splitter ETL Transformer.

For each combination of communication mode and FQN-flag, this test:
  1. Uploads sample audio files into a fresh bucket.
  2. Initializes the Audio Splitter ETL with fixed from/to times.
  3. Fetches each transformed segment and compares it
     against a locally-trimmed version for bitwise equality.
"""

import logging
from io import BytesIO
from itertools import product
from pathlib import Path
from typing import Dict

import pytest
import soundfile as sf
from aistore.sdk import Bucket
from aistore.sdk.etl import ETLConfig

from tests.const import COMM_TYPES, FQN_OPTIONS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def trim_audio_bytes(buf: bytes, audio_format: str, start: float, end: float) -> bytes:
    """
    Trim `buf` audio between `start` and `end` seconds and return WAV bytes.
    """
    bio = BytesIO(buf)
    with sf.SoundFile(bio, mode="r") as src:
        sr, ch = src.samplerate, src.channels
        start_frame = int(start * sr)
        end_frame = int(end * sr)
        src.seek(start_frame)
        frames = src.read(end_frame - start_frame)

    out = BytesIO()
    with sf.SoundFile(
        out, mode="w", samplerate=sr, channels=ch, format=audio_format
    ) as dst:
        dst.write(frames)
    return out.getvalue()


@pytest.mark.parametrize("comm_type,use_fqn", product(COMM_TYPES, FQN_OPTIONS))
def test_audio_splitter_transform(
    test_bck: Bucket,
    local_audio_files: Dict[str, Path],
    etl_factory,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    Validate the Audio Splitter ETL transformer.

    Args:
        test_bck:        fresh bucket fixture
        local_audio_files: map of filename -> Path for inputs
        etl_factory:     factory to init & cleanup ETLs
        comm_type:       one of COMM_TYPES
        use_fqn:         whether to pass FQN as argument
    """
    # 1) upload
    file_name = "test-audio-wav.wav"
    path = local_audio_files[file_name]
    test_bck.object(file_name).get_writer().put_file(path)

    # 2) init with fixed times
    from_t, to_t = 1.0, 2.0
    args = {"from_time": f"{from_t:.2f}", "to_time": f"{to_t:.2f}"}
    etl_name = etl_factory(
        tag="audio-splitter",
        server_type="fastapi",
        comm_type=comm_type,
        arg_type="fqn" if use_fqn else "",
        direct_put=True,
    )
    logger.info("Initialized ETL %s (comm=%s, fqn=%s)", etl_name, comm_type, use_fqn)

    # 3) fetch & compare
    reader = test_bck.object(file_name).get_reader(etl=ETLConfig(etl_name, args=args))
    transformed = reader.read_all()
    original = Path(path).read_bytes()
    expected = trim_audio_bytes(original, "wav", from_t, to_t)

    assert transformed == expected, f"{file_name}: payload mismatch (ETL={etl_name})"
