"""
Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import logging
import re
from pathlib import Path
from typing import Dict
from itertools import product

import pytest
from aistore.sdk import Bucket
from aistore.sdk.etl import ETLConfig

from tests.const import (
    BATCH_RENAME_TEMPLATE,
    COMM_TYPES,
    FQN_OPTIONS,
)

# Configure module-level logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def _verify_renamed_files(
    bucket: Bucket,
    local_files: Dict[str, Path],
    etl_name: str,
    pattern: str,
    prefix: str,
) -> None:
    """
    Verifies the output of the ETL transformer:
    - Ensures transformed objects match original content.
    - If a filename matches the pattern, it should also appear under a new prefixed name.
    """
    for filename, path in local_files.items():
        original_data = Path(path).read_bytes()
        output_data = (
            bucket.object(filename).get_reader(etl=ETLConfig(etl_name)).read_all()
        )
        assert (
            output_data == original_data
        ), f"{filename} was not echoed correctly by ETL '{etl_name}'"

        if re.match(pattern, filename):
            renamed_path = f"{prefix}{filename}"
            renamed_data = bucket.object(renamed_path).get_reader().read_all()
            assert (
                renamed_data == original_data
            ), f"{filename} was not renamed correctly to {renamed_path}"


@pytest.mark.parametrize("comm_type, use_fqn", product(COMM_TYPES, FQN_OPTIONS))
def test_batch_rename_transformer(
    test_bck: Bucket,
    local_audio_files: Dict[str, Path],
    etl_factory,
    endpoint: str,
    comm_type: str,
    use_fqn: bool,
) -> None:
    """
    Integration test for the Batch Rename ETL transformer.
    Uploads audio files to a bucket, initializes the transformer,
    and verifies renaming behavior using ETL output.
    """
    pattern = r".*\.flac$"
    prefix = "renamed_"

    # Upload input files to the test bucket
    for fname, fpath in local_audio_files.items():
        test_bck.object(fname).get_writer().put_file(str(fpath))

    # Build transformer spec
    transformer_spec = BATCH_RENAME_TEMPLATE.format(
        communication_type="{communication_type}",
        direct_put="{direct_put}",
        command="{command}",
        ais_endpoint=endpoint,
        bck_name=test_bck.name,
        regex_pattern=pattern,
        dst_prefix=prefix,
    )

    # Initialize transformer
    etl_name = etl_factory(
        tag="batch-rename",
        server_type="fastapi",
        template=transformer_spec,
        communication_type=comm_type,
        use_fqn=use_fqn,
        direct_put="true",
    )
    logger.info(
        "Initialized ETL '%s' (server=fastapi, comm=%s, fqn=%s)",
        etl_name,
        comm_type,
        use_fqn,
    )

    # Validate output
    _verify_renamed_files(test_bck, local_audio_files, etl_name, pattern, prefix)
