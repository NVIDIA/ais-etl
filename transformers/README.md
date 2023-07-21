# Sample Transformers

AIStore hosts a variety of sample transformers in the form of Docker images to be used with ETL workflows on AIStore via the [`init spec`](https://github.com/NVIDIA/aistore/blob/master/docs/etl.md#init-spec-request) functionality.

| Transformer | Language | Communication Mechanisms | Description |
| ---------- | -------- | ------------------------ | ----------- |
| `echo` | `python:3.8.5` | `hpull`, `hpush` | Returns the original data, with an `MD5` sum in the response headers. |
| `go_echo` | `golang:1.16` | `hpull`, `hpush` | Returns the original data, with an `MD5` sum in the response headers. |
| `hello_world` | `python:3.8.5` | `hpull`, `hpush` | Returns `Hello World!` string on any request. |
| `md5` | `python:3.8.5` | `hpull`, `hpush` | Returns the `MD5` sum of the original data as the response. |
| `tar2tf` | `golang:1.16` | `hrev` | Returns the transformed TensorFlow compatible data for the input `TAR` files. |
| `compress` | `python:3.8.5` | `hpull`, `hpush` | Returns the compressed or decompressed data using `gzip` or `bz2`. |

## General Usage

The following sections demonstrate initializing ETLs on AIStore using the provided sample transformers.

> For detailed usage information regarding the `Tar2TF` and `Compress` transformers and their optional parameters, please refer to the `README` documents located in their respective sub-directories.

#### Pre-Requisites

[ETLs](https://github.com/NVIDIA/aistore/blob/master/docs/etl.md) on AIStore requires the installation and use of Kubernetes.

> For more information on AIStore Kubernetes deployment options, refer [here](https://github.com/NVIDIA/aistore/blob/master/docs/etl.md#kubernetes-deployment).

### Usage w/ AIStore CLI

The basic procedure is as follows: 

1. Change directory into sub-directory of desired sample transformer. 
2. Export communication mechanism (and optional arguments if any) as environment variables.
3. Substitute environment variables into the provided `YAML` specification file (`pod.yaml`).
4. Initialize ETL w/ AIStore CLI providing path to the generated `YAML` specification file.

The following demonstrates basic usage:

```bash
# Change Directory (to Desired Sample Transformer)
cd ais-etl/transformers/md5

# Export Environment Variables for Communication Mechanism (& Any Additional Arguments)
export COMMUNICATION_TYPE = "hpull://"

# Subsitute Environment Variables in YAML Specificiation
eval "echo \"$(cat pod.yaml)\"" > md5_pod_config.yaml

# Initialize ETL on AIStore via CLI
ais etl init spec --name md5-etl --from-file "./md5_pod_config.yaml"
```

### Usage w/ AIStore Python SDK

The `YAML` specification files for the sample transformers are provided as [templates](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/etl_templates.py) in the [Python SDK](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/README.md).

The basic procedure is as follows: 

1. Import desired sample transformer's YAML specification template. 
2. Format communication mechanism (and optional arguments if any) into template.
3. Initialize ETL w/ AIStore SDK providing the formatted template.

The following demonstrates basic usage:

```python
from aistore.sdk.client import Client
from aistore.sdk.etl_templates import ECHO
from aistore.sdk.etl_const import ETL_COMM_HPULL

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

echo_etl_template = ECHO.format(communication_type=ETL_COMM_HPULL)

client.etl("echo-etl").init_spec(template=echo_etl_template, communication_type=ETL_COMM_HPULL)
```

## Contribution

The maintenance of the sample transformers on [DockerHub](https://hub.docker.com/u/aistorage) is managed by the [`ais-etl`](https://github.com/NVIDIA/ais-etl) GitHub repository. 

To contribute, push any changes to sample transformers to the GitHub repository. The existing GitHub workflows will build and push the updated sample transformers to the [DockerHub](https://hub.docker.com/u/aistorage) repostiory.

> For more information, refer to the GitHub workflow files [here](https://github.com/NVIDIA/ais-etl/tree/master/.github/workflows).

## References

- [Python SDK](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/README.md)
- [AIStore CLI](https://github.com/NVIDIA/aistore/blob/master/docs/cli.md)
- [AIS-ETL](https://github.com/NVIDIA/aistore/blob/master/docs/etl.md)
