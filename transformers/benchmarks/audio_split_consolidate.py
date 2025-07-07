"""
Benchmarking script for audio processing pipeline with AIS Transformers.
Generates test data, runs ETL transformations, and measures performance.
"""

import os
import json
import logging
import time
from dataclasses import dataclass
from textwrap import dedent
from typing import Generator, Dict, Any, Optional
from io import BytesIO
import tarfile


from aistore import Client
import soundfile as sf


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:  # pylint: disable=missing-class-docstring,too-many-instance-attributes
    # Data generation parameters
    total_manifests: int = 1000
    total_audio_files: int = 100
    entries_per_manifest: int = 100
    parts_per_audio: int = 3
    audio_file_path: str = "<path-to-audio-file>/test-audio-wav.wav"

    # AIS configuration
    endpoint: str = "http://10.52.160.18:51080"
    manifest_bucket: str = "bench_manifests"
    audio_bucket: str = "bench_audio_files"
    dest_bucket: str = "transformed_manifests"

    # ETL configuration
    audio_split_image: str = "aistorage/transformer_audio_splitter:latest"
    audio_split_etl: str = "transformer-audio-splitter"
    audio_manager_image: str = "aistorage/transformer_audio_manager:latest"
    audio_manager_etl: str = "transformer-audio-manager"

    # Transformation parameters
    transformation_timeout: str = "20m"
    job_wait_timeout: int = 1200  # seconds


class Timer:
    """Context manager for timing code blocks."""

    def __init__(self):
        self.start = None
        self.end = None
        self.elapsed = None

    def __enter__(self) -> "Timer":
        self.start = time.time()
        return self

    def __exit__(self, *exc) -> None:
        self.end = time.time()
        self.elapsed = self.end - self.start


def generate_manifest_entries(cfg: BenchmarkConfig) -> Generator[str, None, None]:
    """Generate JSONL entries for manifest files."""
    for entry_id in range(cfg.entries_per_manifest):
        audio_id = f"audio{entry_id:03d}"
        for part in range(cfg.parts_per_audio):
            yield json.dumps(
                {
                    "id": audio_id,
                    "part": part,
                    "from_time": round(0.00 + part, 2),
                    "to_time": round(1.00 + part, 2),
                    "duration": 1,
                    "total_parts": cfg.parts_per_audio,
                }
            )


def create_manifest_content(cfg: BenchmarkConfig) -> bytes:
    """Generate complete manifest JSONL content as bytes."""
    logger.info("Generating manifest content")
    entries = generate_manifest_entries(cfg)
    return "\n".join(entries).encode("utf-8")


def initialize_bucket(client: Client, bucket_name: str) -> None:
    """Initialize a clean bucket for testing."""
    bucket = client.bucket(bucket_name)
    bucket.delete(missing_ok=True)
    bucket.create(exist_ok=True)
    logger.info("Initialized bucket %s", bucket_name)


def upload_files(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    client: Client,
    bucket_name: str,
    file_count: int,
    content: bytes,
    file_prefix: str,
    file_suffix: str = "",
) -> None:
    """Upload multiple files to a bucket."""
    bucket = client.bucket(bucket_name)
    logger.info("Uploading %d files to %s...", file_count, bucket_name)

    for i in range(file_count):
        obj_name = f"{file_prefix}{i:03d}{file_suffix}"
        bucket.object(obj_name).get_writer().put_content(content)

    logger.info("Completed upload to %s", bucket_name)


def setup_benchmark_data(client: Client, cfg: BenchmarkConfig) -> None:
    """Set up all required test data in AIS."""
    with Timer() as timer:
        # Generate manifest content once
        manifest_content = create_manifest_content(cfg)

        # Initialize buckets
        initialize_bucket(client, cfg.manifest_bucket)
        initialize_bucket(client, cfg.audio_bucket)
        initialize_bucket(client, cfg.dest_bucket)

        # Upload manifests
        upload_files(
            client=client,
            bucket_name=cfg.manifest_bucket,
            file_count=cfg.total_manifests,
            content=manifest_content,
            file_prefix="manifest",
            file_suffix=".jsonl",
        )

        with open(cfg.audio_file_path, "rb") as file:
            # Upload audio files
            upload_files(
                client=client,
                bucket_name=cfg.audio_bucket,
                file_count=cfg.total_audio_files,
                content=file.read(),
                file_prefix="audio",
                file_suffix=".wav",
            )

    logger.info("Benchmark data setup completed in %.2f seconds", timer.elapsed)


def get_etl_template(template_type: str, cfg: BenchmarkConfig) -> str:
    """Return ETL template based on type."""
    templates = {
        "split": dedent(
            f"""
            apiVersion: v1
            kind: Pod
            metadata:
              name: {cfg.audio_split_etl}
              annotations:
                communication_type: "hpull://"
                wait_timeout: 10m
            spec:
              containers:
                - name: server
                  image: {cfg.audio_split_image}
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
        ),
        "manager": dedent(
            f"""
            apiVersion: v1
            kind: Pod
            metadata:
              name: {cfg.audio_manager_etl}
              annotations:
                communication_type: "hpull://"
                wait_timeout: 10m
            spec:
              containers:
                - name: server
                  image: {cfg.audio_manager_image}
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
                      value: "{cfg.endpoint}"
                    - name: SRC_BUCKET
                      value: "{cfg.audio_bucket}"
                    - name: SRC_PROVIDER
                      value: "ais"  
                    - name: OBJ_PREFIX
                      value: ""
                    - name: OBJ_EXTENSION
                      value: "wav"
                    - name: ETL_NAME
                      value: "{cfg.audio_split_etl}"
                    - name: DIRECT_FROM_TARGET
                      value: "true"
            """
        ),
    }
    return templates[template_type].strip()


def manage_etl(
    client: Client, cfg: BenchmarkConfig, action: str, comm_type: str = "hpull"
) -> None:
    """Handle ETL lifecycle operations."""
    for etl_name, etl_type in [
        (cfg.audio_split_etl, "split"),
        (cfg.audio_manager_etl, "manager"),
    ]:
        try:
            if action == "init":
                template = get_etl_template(etl_type, cfg)
                client.etl(etl_name).init_spec(
                    template=template, communication_type=comm_type, timeout="10m"
                )
                logger.info("Initialized ETL: %s", etl_name)
            elif action == "cleanup":
                client.etl(etl_name).stop()
                client.etl(etl_name).delete()
                logger.info("Cleaned up ETL: %s", etl_name)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error processing ETL %s: %s", etl_name, str(e))


def execute_transformation(client: Client, cfg: BenchmarkConfig) -> None:
    """Run and monitor the transformation job."""
    logger.info("Starting transformation job...")
    bucket = client.bucket(cfg.manifest_bucket)

    with Timer() as timer:
        job_id = bucket.transform(
            etl_name=cfg.audio_manager_etl,
            to_bck=client.bucket(cfg.dest_bucket),
            ext={"jsonl": "tar"},
            timeout=cfg.transformation_timeout,
        )
        logger.info("Started transformation job ID: %s", job_id)
        client.job(job_id).wait(timeout=cfg.job_wait_timeout, verbose=False)

    mins, secs = divmod(timer.elapsed, 60)
    logger.info("Transformation completed in %d:%05.2f", int(mins), secs)


def trim_audio(  # pylint: disable=too-many-locals
    cfg: BenchmarkConfig, data: dict, client: Client
) -> Optional[bytes]:
    """Trim audio bytes from start_time to end_time."""
    # Get audio file from AIStore
    audio_bytes = (
        client.bucket(cfg.audio_bucket)
        .object(data["id"] + ".wav")
        .get_reader()
        .read_all()
    )
    if not audio_bytes:
        logger.error("No audio data found for trimming.")
    try:
        audio_buffer = BytesIO(audio_bytes)
        audio_format = "wav"  # Assuming WAV format for simplicity
        start_time = data.get("from_time")
        end_time = data.get("to_time")

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
        return trimmed_bytes
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Failed to trim audio: %s", e)
        return None


def process_json_line(line: str) -> Optional[Dict[str, Any]]:
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


def create_tar_archive(
    cfg: BenchmarkConfig, input_bytes: bytes, client: Client
) -> bytes:
    """Create tar archive from JSONL input containing audio processing instructions."""
    output_tar = BytesIO()

    try:
        with tarfile.open(fileobj=output_tar, mode="w") as tar:
            for line_number, line in enumerate(input_bytes.decode().splitlines(), 1):
                if not line.strip():
                    continue

                if (data := process_json_line(line)) is None:
                    logging.info("Skipping invalid line %d : %s", line_number, line)
                    continue

                try:
                    audio_content = trim_audio(cfg, data, client)
                    tar_info = tarfile.TarInfo(name=f"{data['id']}_{data['part']}.wav")
                    tar_info.size = len(audio_content)
                    tar.addfile(tar_info, BytesIO(audio_content))
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logging.error("Failed to process line %d: %s", line_number, e)
        return output_tar.getvalue()
    except Exception as e:
        logging.error("Tar creation failed: %s", e)
        raise


def run_local_transformation(cfg: BenchmarkConfig, client: Client) -> None:
    """Run local transformation for testing."""
    logger.info("Running local transformation...")
    manifest_content = create_manifest_content(cfg)

    with Timer() as timer:
        manifest_bucket = client.bucket(cfg.manifest_bucket)
        objs = manifest_bucket.list_all_objects()
        for obj in objs:
            obj_name = obj.object.name
            manifest_content = manifest_bucket.object(obj_name).get_reader().read_all()
            tar_bytes = create_tar_archive(cfg, manifest_content, client)
            base_obj_name, _ = os.path.splitext(obj_name)
            client.bucket(cfg.dest_bucket).object(
                f"{base_obj_name}.tar"
            ).get_writer().put_content(tar_bytes)

    mins, secs = divmod(timer.elapsed, 60)
    logger.info("Local transformation completed in %d:%05.2f", int(mins), secs)


def benchmark(
    client: Client, cfg: BenchmarkConfig, comm_type: str
):  # pylint: disable=missing-function-docstring
    # Initialize ETLs
    manage_etl(client, cfg, "init", comm_type)

    # Run transformation
    execute_transformation(client, cfg)

    # Cleanup ETLs
    manage_etl(client, cfg, "cleanup")


def main() -> None:
    """Main benchmark execution flow."""
    cfg = BenchmarkConfig()
    client = Client(cfg.endpoint, max_pool_size=100, timeout=300)

    # Setup test data
    setup_benchmark_data(client, cfg)

    for comm_type in ["hpull", "hpush"]:
        initialize_bucket(client, cfg.dest_bucket)
        logger.info("Running benchmark with communication type: %s", comm_type)
        benchmark(client, cfg, comm_type)

    initialize_bucket(client, cfg.dest_bucket)
    run_local_transformation(cfg, client)

    logger.info("Benchmark execution completed")


if __name__ == "__main__":
    main()
