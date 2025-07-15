"""
PyTest fixtures for AIStore ETL transformer tests.

Provides:
- `client`: singleton AIS cluster client
- `test_bck`: ephemeral bucket per test
- `local_files`: map of test-file names to local paths
- `etl_factory`: function to create and auto-clean ETLs

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

# pylint: disable=redefined-outer-name
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from aistore import Client
from aistore.sdk.errors import ErrETLNotFound

from tests.utils import (
    generate_random_string,
    log_etl,
)
from tests.const import SERVER_COMMANDS

logger = logging.getLogger(__name__)
DEFAULT_ENDPOINT = "http://192.168.49.2:8080"

# Constants for stress tests
STRESS_OBJECT_SIZE = 1 * 1024 * 1024  # 1 MiB
NUM_THREADS = 64


@pytest.fixture(scope="session")
def endpoint() -> str:
    """
    Return the AIS endpoint from the environment variable or default to localhost.
    """
    return os.environ.get("AIS_ENDPOINT", DEFAULT_ENDPOINT)


@pytest.fixture(scope="session")
def client(endpoint) -> Client:
    """
    Create a shared AIS cluster client once per test session.
    """
    logger.debug("Connecting to AIS cluster at %s", endpoint)
    client = Client(endpoint)
    return client


@pytest.fixture
def test_bck(client: Client) -> Client.bucket:
    """
    Create a fresh bucket for each test, then delete it at teardown.
    Bucket name is randomized to avoid collisions.
    """
    name = f"test-bucket-{generate_random_string(8)}"
    logger.debug("Creating test bucket %s", name)
    bck = client.bucket(name).create(exist_ok=True)
    yield bck
    logger.debug("Deleting test bucket %s", name)
    bck.delete()


@pytest.fixture
def local_files() -> Dict[str, Path]:
    """
    Provide a mapping of test filenames to local file paths.
    Tests can iterate over these to upload inputs.
    """
    base = Path(__file__).parent / "resources"
    return {
        "test-image.jpg": base / "test-image.jpg",
        "test-text.txt": base / "test-text.txt",
    }


@pytest.fixture
def local_audio_files() -> Dict[str, Path]:
    """
    Provide a mapping of test filenames to local file paths.
    Tests can iterate over these to upload inputs.
    """
    base = Path(__file__).parent / "resources"
    return {
        "test-audio-flac.flac": base / "test-audio-flac.flac",
        "test-audio-mp3.mp3": base / "test-audio-mp3.mp3",
        "test-audio-wav.wav": base / "test-audio-wav.wav",
    }


@pytest.fixture
def etl_factory(client: Client):
    """
    Return a factory that initializes an ETL on the cluster and
    automatically stops & deletes it at test teardown.

    Usage:
        etl_name = etl_factory(tag="hello-world")

    With optional parameters:
        etl_name = etl_factory(
            tag="hello-world",
            server_type="fastapi",
            comm_type="hpull",
            arg_type="fqn",
            direct_put=True,
            ENV_VAR_NAME="value",
        )

    After the test completes, every ETL created via this factory will
    have its logs dumped, then be stopped and deleted.
    """
    created: list[str] = []

    def _create(
        tag: str,
        server_type: str = "fastapi",
        **kwargs,
    ) -> str:
        """
        Initialize one ETL spec.

        Args:
            tag: short identifier (e.g. "echo" or "hello-world")
            server_type: key in SERVER_COMMANDS ("flask"/"fastapi"/"http")
            **kwargs: any additional parameters for init() method (optional)
        Returns:
            The unique ETL name created.
        """
        comm_type = kwargs.get("comm_type", "hpull")
        suffix = generate_random_string(6)
        name = f"{tag[:10]}-{server_type}-{comm_type}-{suffix}"
        created.append(name)

        # Get the image name, handling GIT_TEST logic
        image_tag = tag.replace("-", "_")
        use_test_tag = os.getenv("GIT_TEST", "false").lower() == "true"
        tag_suffix = "test" if use_test_tag else "latest"
        image = f"aistorage/transformer_{image_tag}:{tag_suffix}"

        # Get the command for the server type
        command = None
        if server_type in SERVER_COMMANDS:
            command = SERVER_COMMANDS[server_type]

        logger.debug(
            "Initializing ETL %s with image %s and command %s", name, image, command
        )

        # Init the ETL on the cluster
        client.etl(name).init(image=image, command=command, **kwargs)
        logger.debug("Initialized ETL %s", name)
        return name

    yield _create

    # teardown: for every ETL we created, dump logs, stop, delete
    for name in created:
        try:
            logger.debug("Dumping logs for ETL %s", name)
            log_etl(client, name)

            logger.debug("Stopping ETL %s", name)
            client.etl(name).stop()

            logger.debug("Deleting ETL %s", name)
            client.etl(name).delete()
        except ErrETLNotFound:
            logger.warning("ETL %s not found during cleanup", name)


@pytest.fixture(scope="session")
def stress_object_count() -> int:
    """
    Return the number of objects to use in stress tests.
    This is a session-scoped fixture to avoid re-creation.
    """
    return 10_000


@pytest.fixture(scope="session")
def stress_client() -> Client:
    """
    Create a singleton Client for stress tests.
    """
    endpoint = os.environ.get("AIS_ENDPOINT", DEFAULT_ENDPOINT)
    return Client(endpoint, max_pool_size=100)


@pytest.fixture(scope="session")
def stress_bucket(stress_client: Client, stress_object_count: int) -> Client.bucket:
    """
    Create (once per session) a bucket with `stress_object_count` random 1 MiB objects.
    If the bucket already contains OBJECT_COUNT objects, we skip re-creation.

    Yields:
        The Bucket instance to use as source for all stress tests.
    """
    name = "stress-test-bck"
    bck = stress_client.bucket(name)
    bck.create(exist_ok=True)

    # check how many are already there
    existing = list(bck.list_all_objects())
    if len(existing) != stress_object_count:
        logger.info(
            "Resetting bucket %s (%d objects exist, need %d)",
            name,
            len(existing),
            stress_object_count,
        )
        bck.delete()
        bck.create(exist_ok=True)

        logger.info(
            "Uploading %d objects of %d bytes via %d threads",
            stress_object_count,
            STRESS_OBJECT_SIZE,
            NUM_THREADS,
        )

        def upload(i: int) -> None:
            obj = f"object-{i:05d}.bin"
            bck.object(obj).get_writer().put_content(os.urandom(STRESS_OBJECT_SIZE))

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as exe:
            futures = {exe.submit(upload, i): i for i in range(stress_object_count)}
            for count, future in enumerate(as_completed(futures), start=1):
                future.result()
                if count % 1000 == 0:
                    logger.info("  • uploaded %d/%d …", count, stress_object_count)

        logger.info("Uploaded %d objects to bucket %s", stress_object_count, name)
    else:
        logger.info(
            "Bucket %s already has %d objects; skipping upload",
            name,
            stress_object_count,
        )

    yield bck

    # No teardown: we want to keep the stress data around for the entire session


# pylint: disable=fixme
@pytest.fixture(scope="session")
def stress_audio_bucket(stress_client: Client) -> Client.bucket:
    """
    Stress test bucket for audio files.

    Contains the LibriSpeech dataset, which is a large corpus of
    read English speech. The dataset is used for training and evaluating
    automatic speech recognition (ASR) systems.
    The dataset is available at: http://www.openslr.org/12/

    For this test, we use a subset of the dataset, which is
    training set of 100 hours "clean" speech
    https://www.openslr.org/resources/12/train-clean-100.tar.gz
    """
    name = "LibriSpeech"
    bck = stress_client.bucket(name)
    # TODO: create bucket and download the dataset if it doesn't exist
    yield bck

    # No teardown: we want to keep the stress data around for the entire session


# Duration recorder fixture
@pytest.fixture(scope="module")
def stress_metrics():
    """
    Collects (label, duration) tuples; writes out metrics.txt after tests.
    """
    metrics: List[Tuple[str, float]] = []
    yield metrics
    # Teardown: write sorted metrics
    metrics.sort(key=lambda x: x[1])
    with open("metrics.txt", "a", encoding="utf-8") as f:
        f.write("-" * 72 + "\n")
        header = (
            f"{'Name':<12} | {'Webserver':<9} | "
            f"{'Comm':<6} | {'Arg':<4} | "
            f"{'Direct Put':<12} | Duration\n"
        )
        f.write(header)
        f.write("-" * 72 + "\n")
        for label, dur in metrics:
            line = f"{label}{dur}"
            logger.info(line)
            f.write(line + "\n")
        f.write("-" * 72 + "\n")
        f.write("\n\n")
