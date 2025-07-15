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
import tarfile
import json

import pytest
from aistore.sdk import Bucket
from aistore.sdk.etl import ETLConfig

from tests.const import (
    COMM_TYPES,
    FQN_OPTIONS,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def fetch_etl_audio(
    bucket: Bucket, object_key: str, etl_name: str, args: Dict[str, str]
) -> bytes:
    """
    Fetch a single transformed object via ETL and return its raw bytes.
    """
    reader = bucket.object(object_key).get_reader(
        etl=ETLConfig(name=etl_name, args=args), direct=True
    )
    return reader.read_all()


def parse_manifest_line(line: str) -> Dict[str, str] | None:
    """
    Parse one JSONL line into a dict if it contains the keys
    id, part, from_time, to_time; else return None.
    """
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        logger.error("Invalid JSON: %s", line)
        return None

    required = {"id", "part", "from_time", "to_time"}
    if not required.issubset(entry):
        logger.warning("Missing fields in manifest: %s", line)
        return None

    return entry  # type: ignore[return-value]


def build_expected_tar(
    bucket: Bucket, manifest_bytes: bytes, splitter_etl: str
) -> bytes:
    """
    Locally replay the splitter ETL for each line in `manifest_bytes`
    and bundle the results into a tar archive, returning it as bytes.
    """
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for _, raw in enumerate(manifest_bytes.splitlines(), start=1):
            if not raw.strip():
                continue

            entry = parse_manifest_line(raw)
            if entry is None:
                continue

            # fetch and trim
            obj_key = f"{entry['id']}.wav"
            segment = fetch_etl_audio(bucket, obj_key, splitter_etl, entry)

            member = tarfile.TarInfo(name=f"{entry['id']}_{entry['part']}.wav")
            member.size = len(segment)
            tar.addfile(member, BytesIO(segment))

    return buf.getvalue()


def compare_tar_contents(actual: bytes, expected: bytes) -> None:
    """
    Assert that two tar archives contain the same members with identical bytes.
    """

    def extract_all(tar_bytes: bytes) -> Dict[str, bytes]:
        d: Dict[str, bytes] = {}
        with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r") as t:
            for m in t.getmembers():
                if m.isfile():
                    d[m.name] = t.extractfile(m).read()  # type: ignore[union-attr]
        return d

    act = extract_all(actual)
    exp = extract_all(expected)

    assert act.keys() == exp.keys(), "Tar member sets differ"
    for name, content in act.items():
        assert content == exp[name], f"Content mismatch for {name}"


@pytest.mark.parametrize("comm_type,use_fqn", product(COMM_TYPES, FQN_OPTIONS))
def test_audio_split_consolidate_transform(
    endpoint: str,
    test_bck: Bucket,
    etl_factory,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    - Upload one WAV + one JSONL manifest.
    - Create splitter ETL that chops WAV → segments.
    - Create manager ETL that bundles segments into a tar.
    - Fetch manager ETL output and compare vs our local tar.
    """
    # 1) prepare resource paths
    res_dir = Path(__file__).parent / "resources"
    wav_name = "test-audio-wav.wav"
    manifest_name = "test-manifest.jsonl"
    wav_path = res_dir / wav_name
    manifest_path = res_dir / manifest_name

    test_bck.object(wav_name).get_writer().put_file(wav_path)
    test_bck.object(manifest_name).get_writer().put_file(manifest_path)

    # 2) init ETLs

    splitter_etl = etl_factory(
        tag="audio-splitter",
        server_type="fastapi",
        comm_type=comm_type,
        arg_type="fqn" if use_fqn else "",
        direct_put=True,
    )

    manager_etl = etl_factory(
        tag="audio-manager",
        server_type="fastapi",
        comm_type=comm_type,
        arg_type="fqn" if use_fqn else "",
        direct_put=True,
        AIS_ENDPOINT=endpoint,
        SRC_BUCKET=test_bck.name,
        SRC_PROVIDER="ais",
        OBJ_PREFIX="",
        OBJ_EXTENSION="wav",
        ETL_NAME=splitter_etl,
    )

    # Fetch actual tar from manager ETL
    actual_tar = (
        test_bck.object(manifest_name)
        .get_reader(etl=ETLConfig(name=manager_etl))
        .read_all()
    )

    # Build expected tar locally & compare
    manifest_bytes = manifest_path.read_bytes()
    expected_tar = build_expected_tar(test_bck, manifest_bytes, splitter_etl)
    compare_tar_contents(actual_tar, expected_tar)
