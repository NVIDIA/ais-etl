# Compress Transformer

The `Compress` transformer employs compression algorithms such as `gzip` and `bz2` to compress or decompress data. 

The transformer supports both `hpull` and `hpush` communication mechanisms.

> For more information on communication mechanisms, refer [here](https://github.com/NVIDIA/aistore/blob/master/docs/etl.md#communication-mechanisms).

## Available Parameters

The `Compress` transformer supports a range of arguments:

| Argument    | Description                                                           | Default Value |
| ----------- | --------------------------------------------------------------------- | ------------- |
| `--mode`      | Specify the data processing mode to use (e.g., `compress` or `decompress`) | `compress`     |
| `--compression`| Specify the compression algorithm to use (e.g., `gzip` or `bz2`)           | `gzip`          |

Remember to adjust these parameters according to your requirements.

## Basic Usage (w/ Defaults)

By default, the `Compress` transformer compresses data using the `gzip` algorithm. The following sections demonstrate how to use the transformer with default options.

### Initialization w/ AIStore CLI

The following demonstrates how to initialize the `Compress` transformer with its default settings using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/master/docs/cli.md):

```bash
cd ais-etl/transformers/compress

# Export Communication Mechanism as Environment Variable
export COMMUNICATION_TYPE = 'hpull://'
# Substitute Environment Variables in Pod Spec
eval "echo \"$(cat pod.yaml)\"" > compresssion_pod_config.yaml 
# Initialize Default Compression ETL
ais etl init spec --name 'compression-etl' --from-file './compression_pod_config.yaml'
```

### Initialization w/ AIStore Python SDK

The following demonstrates how to initialize the `Compress` transformer with its default settings using the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/README.md):

```python
from aistore.sdk.client import Client
# Import Compress YAML Specification
from aistore.sdk.etl_templates import COMPRESS
# Import Communication Mechanism
from aistore.sdk.etl_const import ETL_COMM_HPULL

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

# Format Template w/ Communication Mechanism & Default Server Arguments
compress_template = COMPRESS.format(
    communication_mechanism=ETL_COMM_PULL,
    arg1='',
    val1='',
    arg2='',
    val2='',
)

# Initialize Default Compress ETL
compress_template = client.etl("gzip-compression-etl").init_spec(template=compress_template, communication_type=ETL_COMM_HPULL)
```

## Compression Options

The `Compress` transformer can be used in different modes (compress or decompress) and with different compression algorithms (gzip or bz2). The following sections demonstrate how to use these options.

### Initialization w/ AIStore CLI

The following demonstrates how to initialize the `Compress` transformer with different settings via the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/master/docs/cli.md):

```bash
cd ais-etl/transformers/compress

# Export Communication Mechanism & Server Arguments as Environment Variables
export COMMUNICATION_TYPE = 'hpull://'
export ARG1 = '--mode'
export VAL1 = 'decompress'
export ARG2 = '--compression'
export VAL2 = 'bz2'
# Substitute Environment Variables in Pod Spec
eval "echo \"$(cat pod.yaml)\"" > decompresssion_pod_config.yaml 
# Initialize Decompression ETL
ais etl init spec --name 'decompression-etl' --from-file './decompression_pod_config.yaml'
```

### Initialization w/ AIStore Python SDK

The following demonstrates how to initialize the `Compress` transformer with different settings via the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/README.md):

```python
from aistore.sdk.client import Client
# Import Compress YAML Specification
from aistore.sdk.etl_templates import COMPRESS
# Import Communication Mechanism
from aistore.sdk.etl_const import ETL_COMM_HPULL

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

# Format Template w/ Communication Mechanism & Additional Server Arguments
decompress_template = COMPRESS.format(
    communication_mechanism=ETL_COMM_HPULL,
    arg1='--mode',
    val1='decompress',
    arg2='--compression',
    val2='bz2'   
)

# Initialize ETLs
decompress_template = client.etl("bz2-decompression-etl").init_spec(template=decompress_template, communication_type=ETL_COMM_HPULL)
```

## References

- [Python SDK](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/README.md)
- [AIStore CLI](https://github.com/NVIDIA/aistore/blob/master/docs/cli.md)
- [AIS-ETL](https://github.com/NVIDIA/aistore/blob/master/docs/etl.md)
