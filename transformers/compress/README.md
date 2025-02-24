# Compress Transformer

The `Compress` transformer employs compression algorithms such as `gzip` and `bz2` to compress or decompress data. 

The transformer supports both `hpull` and `hpush` communication mechanisms.

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

The following demonstrates how to initialize the `Compress` transformer w/ default parameters using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md):

```bash
cd ais-etl/transformers/compress

# Export Communication Mechanism as Environment Variable
export COMMUNICATION_TYPE = 'hpull://'
# Export COMPRESS_OPTIONS as Environment Variable
export COMPRESS_OPTIONS = '{}'
# Substitute Environment Variables in Pod Spec
eval "echo \"$(cat pod.yaml)\"" > gzip_compresssion_pod_config.yaml 
# Initialize Default Compression ETL
ais etl init spec --name 'gzip-compression-etl' --from-file './gzip_compression_pod_config.yaml'
```

The following demonstrates how to initialize the `Compress` transformer w/ parameter specifications using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md):

```bash
cd ais-etl/transformers/compress

# Export Communication Mechanism as Environment Variable
export COMMUNICATION_TYPE = 'hpull://'
# Export COMPRESS_OPTIONS as Environment Variable
export COMPRESS_OPTIONS = '{"mode": "decompress", "compression": "bz2"}'

# Substitute Environment Variables in Pod Spec
eval "echo \"$(cat pod.yaml)\"" > bz2_decompresssion_pod_config.yaml 
# Initialize Decompression ETL
ais etl init spec --name 'bz2-decompression-etl' --from-file './bz2_decompression_pod_config.yaml'
```

### Initialization w/ AIStore Python SDK

The following demonstrates how to initialize the `Compress` transformer with w/ default parameters using the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md):

```python
import json

from aistore.sdk.client import Client
# Import Compress YAML Specification
from aistore.sdk.etl_templates import COMPRESS
# Import Communication Mechanism
from aistore.sdk.etl_const import ETL_COMM_HPULL

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

compress_options = json.dumps('{}')

# Format Template w/ Communication Mechanism & Default Server Arguments
compress_template = COMPRESS.format(
    communication_mechanism=ETL_COMM_PULL,
    compress_options=compress_options
    
)

# Initialize Default Compress ETL
compress_template = client.etl("gzip-compression-etl").init_spec(template=compress_template, communication_type=ETL_COMM_HPULL)
```

The following demonstrates how to initialize the `Compress` transformer w/ parameter specifications via the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md):

```python
from aistore.sdk.client import Client
# Import Compress YAML Specification
from aistore.sdk.etl_templates import COMPRESS
# Import Communication Mechanism
from aistore.sdk.etl_const import ETL_COMM_HPULL

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

compress_options = json.dumps({"mode": "decompress", "compression": "bz2"})

# Format Template w/ Communication Mechanism & Additional Server Arguments
decompress_template = COMPRESS.format(
    communication_mechanism=ETL_COMM_HPULL,
    compress_options = compress_options
)

# Initialize ETLs
decompress_template = client.etl("bz2-decompression-etl").init_spec(template=decompress_template, communication_type=ETL_COMM_HPULL)
```

## References

- [Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md)
- [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md)
- [AIS-ETL](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md)
