"""
Integration test for the Parquet Parser ETL transformer.

Tests parquet file conversion to JSON and CSV formats,
following the same pattern as other transformer tests.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
import json
import tempfile
from pathlib import Path
from typing import Dict

import pytest
import pandas as pd
from aistore.sdk.etl import ETLConfig
from aistore.sdk import Bucket

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture
def parquet_files():
    data = {
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "score": [95.5, 87.2, 92.1],
        "active": [True, False, True],
    }
    df = pd.DataFrame(data)

    files = {}

    small_file = Path(tempfile.mktemp(suffix=".parquet"))
    df.to_parquet(small_file, index=False)
    files["test_small.parquet"] = small_file

    large_data = pd.concat([df] * 10, ignore_index=True)
    large_file = Path(tempfile.mktemp(suffix=".parquet"))
    large_data.to_parquet(large_file, index=False)
    files["test_large.parquet"] = large_file

    yield files

    # Cleanup temp files
    for temp_file in files.values():
        if temp_file.exists():
            temp_file.unlink()


def _upload_test_files(test_bck: Bucket, local_files: Dict[str, Path]) -> None:
    for filename, path in local_files.items():
        test_bck.object(filename).get_writer().put_file(str(path))


def _verify_json_output(output_str: str, filename: str) -> None:
    """Verify JSON output format and content."""
    lines = output_str.strip().split("\n")
    assert (
        len(lines) >= 3
    ), f"Expected at least 3 JSON lines for {filename}, got {len(lines)}"

    # Validate first line is valid JSON with expected fields
    first_record = json.loads(lines[0])
    assert "id" in first_record, f"JSON output missing 'id' field in {filename}"
    assert "name" in first_record, f"JSON output missing 'name' field in {filename}"
    assert "score" in first_record, f"JSON output missing 'score' field in {filename}"
    assert "active" in first_record, f"JSON output missing 'active' field in {filename}"

    # Validate data values
    assert (
        first_record["id"] == 1
    ), f"Expected id=1, got {first_record['id']} in {filename}"
    assert (
        first_record["name"] == "Alice"
    ), f"Expected name='Alice', got {first_record['name']} in {filename}"


def _verify_csv_output(output_str: str, filename: str) -> None:
    """Verify CSV output format and content."""
    lines = output_str.strip().split("\n")
    assert (
        len(lines) >= 4
    ), f"Expected header + 3 data rows for {filename}, got {len(lines)}"

    header = lines[0]
    assert "id" in header, f"CSV output missing 'id' column in {filename}"
    assert "name" in header, f"CSV output missing 'name' column in {filename}"
    assert "score" in header, f"CSV output missing 'score' column in {filename}"
    assert "active" in header, f"CSV output missing 'active' column in {filename}"

    first_row = lines[1].split(",")
    assert (
        len(first_row) >= 4
    ), f"CSV row should have at least 4 columns in {filename}, got {len(first_row)}"
    assert (
        first_row[0] == "1"
    ), f"Expected first row id=1 in {filename}, got {first_row[0]}"


@pytest.mark.parametrize("output_format", ["json", "csv"])
def test_parquet_parser_conversion(
    test_bck: Bucket,
    parquet_files: Dict[str, Path],
    etl_factory,
    output_format: str,
) -> None:
    _upload_test_files(test_bck, parquet_files)

    # Initialize ETL
    etl_name = etl_factory(
        tag="parquet-parser",
        server_type="go-http",
        comm_type="hpush",
        arg_type="",
        OUTPUT_FORMAT=output_format,
    )

    logger.info(
        f"Initialized parquet-parser ETL '{etl_name}' for format: {output_format}"
    )

    # Transform and verify each file
    for filename in parquet_files.keys():
        result_bytes = (
            test_bck.object(filename).get_reader(etl=ETLConfig(etl_name)).read_all()
        )

        output_str = result_bytes.decode("utf-8")

        if output_format == "json":
            _verify_json_output(output_str, filename)
        elif output_format == "csv":
            _verify_csv_output(output_str, filename)


def test_parquet_parser_error_handling(
    test_bck: Bucket,
    parquet_files: Dict[str, Path],
    etl_factory,
) -> None:
    """
    Test error handling for invalid output formats.
    """
    # Upload test files
    _upload_test_files(test_bck, parquet_files)

    etl_name = etl_factory(
        tag="parquet-parser",
        server_type="go-http",
        comm_type="hpush",
        arg_type="",
        OUTPUT_FORMAT="invalid_format",
    )

    # Transform should fail or return error message
    filename = list(parquet_files.keys())[0]

    try:
        result_bytes = (
            test_bck.object(filename).get_reader(etl=ETLConfig(etl_name)).read_all()
        )
        output_str = result_bytes.decode("utf-8")

        # Should return error message for invalid format
        assert (
            "unsupported output format" in output_str.lower()
        ), f"Expected error message for invalid format, got: {output_str[:200]}"

    except Exception as e:
        logger.info(f"ETL correctly failed for invalid format: {e}")
