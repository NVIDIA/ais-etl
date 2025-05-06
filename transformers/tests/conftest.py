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
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from aistore import Client
from aistore.sdk.errors import ErrETLNotFound

from tests.utils import (
    generate_random_string,
    log_etl,
    format_image_tag_for_git_test_mode,
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
        etl_name = etl_factory(
            tag="hello-world",
            server_type="flask",
            template=HELLO_WORLD_TEMPLATE,
            communication_type="hpull",
            use_fqn=True,
        )

    After the test completes, every ETL created via this factory will
    have its logs dumped, then be stopped and deleted.
    """
    created: list[str] = []

    # pylint: disable=too-many-arguments
    def _create(
        tag: str,
        server_type: str,
        template: str,
        communication_type: str,
        use_fqn: bool,
        direct_put: str = "false",
    ) -> str:
        """
        Initialize one ETL spec.

        Args:
            tag: short identifier (e.g. "echo" or "hello-world")
            server_type: key in SERVER_COMMANDS ("flask"/"fastapi"/"http")
            template: Pod-spec YAML template string
            communication_type: ETL_COMM_HPULL or ETL_COMM_HPUSH
            use_fqn: if True, sets arg_type="fqn", else ""
            direct_put: if "true", sets direct_put=true in the template
        Returns:
            The unique ETL name created.
        """
        suffix = generate_random_string(6)
        name = f"{tag[:10]}-{server_type}-{communication_type}-{suffix}"
        created.append(name)

        try:
            cmd = json.dumps(SERVER_COMMANDS[server_type])

            tmpl = template.format(
                communication_type=communication_type,
                command=cmd,
                direct_put=direct_put,
            )
        except KeyError:
            # Other types of servers, like "go", let the template handle it
            tmpl = template.format(
                communication_type=communication_type,
                direct_put=direct_put,
            )

        if os.getenv("GIT_TEST", "false").lower() == "true":
            tmpl = format_image_tag_for_git_test_mode(tmpl, tag.replace("-", "_"))

        logger.debug("Template for ETL %s:\n%s", name, tmpl)

        # Init the ETL on the cluster
        client.etl(name).init_spec(
            template=tmpl,
            communication_type=communication_type,
            arg_type="fqn" if use_fqn else "",
        )
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
