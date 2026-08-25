# Sample Transformers

AIStore hosts a variety of sample transformer images for ETL workflows. Each transformer includes an [`etl_spec.yaml`](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#runtime-specification) runtime specification.

| Transformer | Language | Communication Mechanisms | Description |
| ---------- | -------- | ------------------------ | ----------- |
| [`echo`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/echo) | `python:3.13` | `hpull`, `hpush` | Returns the original data, with an `MD5` sum in the response headers. |
| [`go_echo`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/go_echo) | `golang:1.24` | `hpull`, `hpush` | Returns the original data, with an `MD5` sum in the response headers. |
| [`hello_world`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/hello_world) | `python:3.13` | `hpull`, `hpush` | Returns `Hello World!` string on any request. |
| [`go_hello_world`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/go_hello_world) | `golang:1.24` | `hpull`, `hpush` | Returns `Hello World!` string on any request (Go implementation). |
| [`md5`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/md5) | `python:3.13` | `hpull`, `hpush` | Returns the `MD5` sum of the original data as the response. |
| [`hash_with_args`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/hash_with_args) | `python:3.13` | `hpull`, `hpush` | Returns the `XXHash64` digest of the original data with customizable seed arguments. |
| [`tar2tf`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/tar2tf) | `golang:1.25` | `hpull`, `hpush` | Returns the transformed TensorFlow compatible data for the input `TAR` files. |
| [`compress`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/compress) | `python:3.11` | `hpull`, `hpush` | Returns the compressed or decompressed data using `gzip` or `bz2`. |
| [`FFmpeg`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/FFmpeg) | `python:3.13` | `hpull`, `hpush` | Returns audio files in `WAV` format with control over Audio Channels (`AC`) and Audio Rate (`AR`). |
| [`go_FFmpeg`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/go_FFmpeg) | `golang:1.24` | `hpull`, `hpush` | Returns audio files in `WAV` format with control over Audio Channels (`AC`) and Audio Rate (`AR`) (Go implementation). |
| [`NeMo/audio_split_consolidate`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/NeMo/audio_split_consolidate) | `python:3.13` | `hpull`, `hpush` | Splits and consolidates audio files using JSONL manifests with distributed processing architecture. |
| [`parquet-parser`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/parquet-parser) | `golang:1.24` | `hpush` | Converts Parquet files to JSON, CSV, or TXT formats with concurrent processing and dynamic schema extraction. |
| [`batch_rename`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/batch_rename) | `python:3.13` | `hpull`, `hpush` | Renames objects matching regex patterns and copies them to destination buckets with modified paths. |
| [`face_detection`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/face_detection) | `python:3.11-slim` | `hpull`, `hpush` | Detects faces in images using Single Shot MultiBox Detector (`SSD`) model and returns images with bounding boxes. |
| [`keras`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/keras_preprocess) | `python:3.11-slim` | `hpull`, `hpush` | Returns the transformed images using `Keras` pre-processing. |
| [`torchvision`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/torchvision_preprocess) | `python:3.11-slim` | `hpull`, `hpush` | Returns the transformed images using `Torchvision` pre-processing. |

## General Usage

The following sections demonstrate initializing ETLs on AIStore using the provided sample transformers.

> For detailed usage information and optional parameters for any transformer, please refer to the `README` documents located in their respective sub-directories.

#### Pre-Requisites

[ETLs](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md) on AIStore requires the installation and use of Kubernetes.

> For more information on AIStore Kubernetes deployment options, refer [here](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#kubernetes-deployment).

### Usage w/ AIStore CLI

Initialize a transformer from its `etl_spec.yaml`, which defines the image and optional command, communication type, environment variables, and timeouts.

```bash
# Change Directory (to Desired Sample Transformer)
cd ais-etl/transformers/md5

# Initialize ETL directly from runtime spec
ais etl init -f etl_spec.yaml --name md5-etl

# Transform objects (inline)
ais etl object md5-etl ais://<src-bck>/<obj> -

# Transform bucket-to-bucket
ais etl bucket md5-etl ais://<src-bck> ais://<dst-bck>
```

### Usage w/ AIStore Python SDK

Initialize the same image directly with the Python SDK:

```python
client.etl("md5-etl").init(image="aistorage/transformer_md5:latest")
```

## Contribution

The maintenance of the sample transformers on [DockerHub](https://hub.docker.com/u/aistorage) is managed by the [`ais-etl`](https://github.com/NVIDIA/ais-etl) GitHub repository. 

To contribute, push any changes to sample transformers to the GitHub repository. The existing GitHub workflows will build and push the updated sample transformers to the [DockerHub](https://hub.docker.com/u/aistorage) repostiory.

> For more information, refer to the GitHub workflow files [here](https://github.com/NVIDIA/ais-etl/tree/main/.github/workflows).

## References

- [Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md)
- [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md)
- [AIS-ETL](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md)
