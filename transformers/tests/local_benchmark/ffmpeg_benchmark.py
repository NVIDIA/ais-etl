"""
Local Benchmark for FFmpeg Transformer

Batch-transcode all .flac files in a source AIS bucket to WAV at specified
channels and sampling rate, uploading results to a destination bucket.
Uses concurrent workers and logs progress and summary.

Configuration via environment variables:
  AIS_ENDPOINT: AIS cluster endpoint URL (default http://localhost:8080)
  SRC_BUCKET  : Source bucket name (default LibriSpeech)
  DST_BUCKET  : Destination bucket name (default LibriSpeech-16k)
  WORKERS     : Number of parallel FFmpeg workers (default 24)
  AC          : Number of audio channels in output WAV (default 1)
  AR          : Sample rate in output WAV (default 16000)

Note:
  - Requires ffmpeg installed and available in PATH.
  - Assumes source bucket contains .flac files. In our case,
    we used LibriSpeech Dataset.
  - Destination bucket is reset before processing.
  - For best results, run on a machine in same network (VCN) as AIS cluster.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

# pylint: disable=too-many-locals, broad-exception-caught
import os
import sys
import logging
import subprocess
import time
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from aistore import Client

# Configuration
AIS_ENDPOINT = os.getenv("AIS_ENDPOINT", "http://localhost:8080")
SRC_BUCKET = os.getenv("SRC_BUCKET", "LibriSpeech")
DST_BUCKET = os.getenv("DST_BUCKET", "LibriSpeech-16k")
WORKERS = int(os.getenv("WORKERS", "24"))
CHANNELS = int(os.getenv("AC", "1"))
SAMPLE_RATE = int(os.getenv("AR", "16000"))

FFMPEG_CMD = [
    "ffmpeg",
    "-nostdin",
    "-loglevel",
    "error",
    "-i",
    "pipe:0",
    "-ac",
    str(CHANNELS),
    "-ar",
    str(SAMPLE_RATE),
    "-c:a",
    "pcm_s16le",
    "-f",
    "wav",
    "pipe:1",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ffmpeg_local")


def transcode_flac_to_wav(input_bytes: bytes) -> bytes:
    """
    Transcode FLAC audio bytes to WAV using ffmpeg.

    Parameters:
        input_bytes (bytes): Raw .flac file data.

    Returns:
        bytes: WAV-encoded audio data.

    Raises:
        RuntimeError: If ffmpeg returns a non-zero exit code.
    """

    with subprocess.Popen(
        FFMPEG_CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        out, err = proc.communicate(input=input_bytes)
        if proc.returncode != 0:
            msg = err.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"ffmpeg failed: {msg}")
        return out


def process_object(
    client: Client,
    src_bucket: str,
    dst_bucket: str,
    obj_name: str,
) -> Tuple[str, bool, str]:
    """
    If `obj_name` ends with .flac, fetch it, transcode it, and upload
    as a .wav to dst_bucket.  Otherwise skip.

    Returns:
        (obj_name, success_flag, errmsg_or_empty)
    """
    if not obj_name.lower().endswith(".flac"):
        return obj_name, True, "skipped (not .flac)"

    bck_src = client.bucket(src_bucket)
    bck_dst = client.bucket(dst_bucket)
    try:
        data = bck_src.object(obj_name).get_reader().read_all()
        wav = transcode_flac_to_wav(data)
        new_name = obj_name[:-5] + ".wav"
        bck_dst.object(new_name).get_writer().put_content(wav)
        return obj_name, True, ""
    except Exception as e:
        return obj_name, False, str(e)


def main():
    """
    Main entrypoint: reset destination bucket, list all objects in source, and
    process them in parallel.

    Exit Codes:
        0: all succeeded or skipped
        1: one or more failures occurred
    """
    t0 = time.perf_counter()
    client = Client(AIS_ENDPOINT, max_pool_size=100)
    logger.info("Using AIS endpoint %s", AIS_ENDPOINT)

    # prepare buckets
    src = client.bucket(SRC_BUCKET)
    dst = client.bucket(DST_BUCKET)
    logger.info("Resetting destination bucket %s", DST_BUCKET)
    dst.delete(missing_ok=True)
    dst.create(exist_ok=True)

    # list objects
    objs = [o.name for o in src.list_all_objects()]
    logger.info("Found %d objects in %s", len(objs), SRC_BUCKET)

    successes: List[str] = []
    failures: List[Tuple[str, str]] = []

    # parallel processing
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(process_object, client, SRC_BUCKET, DST_BUCKET, name): name
            for name in objs
        }
        for future in as_completed(futures):
            name = futures[future]
            ok, errmsg = False, ""
            try:
                _, ok, errmsg = future.result()
            except Exception as e:
                errmsg = f"executor error: {e}"
            if ok:
                successes.append(name)
                logger.debug("✅ %s", name)
            else:
                failures.append((name, errmsg))
                logger.error("❌ %s → %s", name, errmsg)

    # summary
    logger.info(
        "Done: %d succeeded, %d failed, %d skipped",
        len(successes),
        len(failures),
        len(objs) - len(successes) - len(failures),
    )
    if failures:
        logger.warning("Failures for %d files. See logs above.", len(failures))
        sys.exit(1)
    t1 = time.perf_counter()
    elapsed = timedelta(seconds=t1 - t0)
    logger.info("Total transformation wall-time: %s", str(elapsed))


if __name__ == "__main__":
    main()
