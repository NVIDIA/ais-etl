# Compress Transformer

The `Compress` transformer employs compression algorithms such as `gzip` and `bz2` to compress or decompress data. 

The transformer is implemented as a FastAPI server and supports both `hpull` and `hpush` communication mechanisms.

> For more information on communication mechanisms, refer [here](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

## Parameters

| Parameter | Description |
|---|---|
| `COMPRESS_OPTIONS` | A JSON string (dictionary) that controls the operation mode and compression algorithm. |

The default operation mode is `compress` and the default compression algorithm is `gzip`. To use these defaults, simply omit them from the input (e.g. `{}` for `gzip` compression).

If you want to specify a different operation mode or compression algorithm, include the `mode` and `compression` keys in the dictionary (e.g.`{"mode": "decompress"}` for `gzip` decompression, `{"compression": "bz2"}` for `bz2` compression).

Remember to adjust these parameters according to your requirements and refer to the following sections for more specific usage examples.

## Usage

The following sections demonstrate usage of the `Compress` transformer using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md) and [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md).

### Initialization w/ AIStore CLI

Initialize the `Compress` transformer with its runtime specification:

```bash
cd ais-etl/transformers/compress

# Initialize Default Compression ETL
ais etl init -f etl_spec.yaml --name gzip-compression-etl
```

To configure a different operation, update `COMPRESS_OPTIONS` in `etl_spec.yaml` before initialization. For example:

```bash
cd ais-etl/transformers/compress

# Set runtime.env[COMPRESS_OPTIONS] to:
# {"mode": "decompress", "compression": "bz2"}
ais etl init -f etl_spec.yaml --name bz2-decompression-etl
```

### Initialization w/ AIStore Python SDK

The following demonstrates how to initialize the `Compress` transformer with w/ default parameters using the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md):

```python
import json
import os

from aistore.sdk.client import Client

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

# Initialize Default Compress ETL
client.etl("gzip-compression-etl").init(
    image="aistorage/transformer_compress:latest",
    comm_type="hpull",
    COMPRESS_OPTIONS=json.dumps({}),
)
```

The following demonstrates how to initialize the `Compress` transformer w/ parameter specifications via the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md):

```python
import json
import os

from aistore.sdk.client import Client

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

compress_options = json.dumps({"mode": "decompress", "compression": "bz2"})

# Initialize ETL
client.etl("bz2-decompression-etl").init(
    image="aistorage/transformer_compress:latest",
    comm_type="hpull",
    COMPRESS_OPTIONS=compress_options,
)
```

## Server Configuration

The transformer runs as a FastAPI server with the following default configuration:

- Server: uvicorn with FastAPI
- Workers: 6 (configurable)
- Host: 0.0.0.0
- Port: 8000
- Access Log: Disabled
- WebSocket Settings:
  - Max Size: 17GB
  - Ping Interval: 0
  - Ping Timeout: 86400s

These settings can be overridden in `etl_spec.yaml`.

## References

- [Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md)
- [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md)
- [AIS-ETL](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md)
