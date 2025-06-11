# Sample Transformers

AIStore hosts a variety of sample transformers in the form of Docker images to be used with ETL workflows on AIStore via the [`init spec`](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#init-spec-request) functionality.

| Transformer | Language | Communication Mechanisms | Description |
| ---------- | -------- | ------------------------ | ----------- |
| [`echo`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/echo) | `python:3.13` | `hpull`, `hpush` | Returns the original data, with an `MD5` sum in the response headers. |
| [`go_echo`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/go_echo) | `golang:1.24` | `hpull`, `hpush` | Returns the original data, with an `MD5` sum in the response headers. |
| [`hello_world`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/hello_world) | `python:3.13` | `hpull`, `hpush` | Returns `Hello World!` string on any request. |
| [`go_hello_world`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/go_hello_world) | `golang:1.24` | `hpull`, `hpush` | Returns `Hello World!` string on any request (Go implementation). |
| [`md5`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/md5) | `python:3.13` | `hpull`, `hpush` | Returns the `MD5` sum of the original data as the response. |
| [`hash_with_args`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/hash_with_args) | `python:3.13` | `hpull`, `hpush` | Returns the `XXHash64` digest of the original data with customizable seed arguments. |
| [`tar2tf`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/tar2tf) | `golang:1.21` | `hpull`, `hpush` | Returns the transformed TensorFlow compatible data for the input `TAR` files. |
| [`compress`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/compress) | `python:3.11` | `hpull`, `hpush` | Returns the compressed or decompressed data using `gzip` or `bz2`. |
| [`FFmpeg`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/FFmpeg) | `python:3.13` | `hpull`, `hpush` | Returns audio files in `WAV` format with control over Audio Channels (`AC`) and Audio Rate (`AR`). |
| [`go_FFmpeg`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/go_FFmpeg) | `golang:1.24` | `hpull`, `hpush` | Returns audio files in `WAV` format with control over Audio Channels (`AC`) and Audio Rate (`AR`) (Go implementation). |
| [`NeMo/audio_split_consolidate`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/NeMo/audio_split_consolidate) | `python:3.13` | `hpull`, `hpush` | Splits and consolidates audio files using JSONL manifests with distributed processing architecture. |
| [`batch_rename`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/batch_rename) | `python:3.13` | `hpull`, `hpush` | Renames objects matching regex patterns and copies them to destination buckets with modified paths. |
| [`face_detection`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/face_detection) | `python:3.8-slim` | `hpull`, `hpush` | Detects faces in images using Single Shot MultiBox Detector (`SSD`) model and returns images with bounding boxes. |
| [`keras`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/keras_preprocess) | `python:3.9-slim` | `hpull`, `hpush` | Returns the transformed images using `Keras` pre-processing. |
| [`torchvision`](https://github.com/NVIDIA/ais-etl/tree/main/transformers/torchvision_preprocess) | `python:3.9-slim` | `hpull`, `hpush` | Returns the transformed images using `Torchvision` pre-processing. |

## General Usage

The following sections demonstrate initializing ETLs on AIStore using the provided sample transformers.

> For detailed usage information and optional parameters for any transformer, please refer to the `README` documents located in their respective sub-directories.

#### Pre-Requisites

[ETLs](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md) on AIStore requires the installation and use of Kubernetes.

> For more information on AIStore Kubernetes deployment options, refer [here](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#kubernetes-deployment).

### Usage w/ AIStore CLI

There are **two** ways to initialize transformers:

#### 1. Runtime-spec (Recommended)

The modern approach uses a compact `etl_spec.yaml` that lists only the image, command, and optionally communication type, environment variables, timeouts, etc.

```bash
# Change Directory (to Desired Sample Transformer)
cd ais-etl/transformers/md5

# Initialize ETL directly from runtime spec
ais etl init spec --from-file etl_spec.yaml md5-etl

# Transform objects (inline)
ais etl object md5-etl ais://<src-bck>/<obj> -

# Transform bucket-to-bucket
ais etl bucket md5-etl ais://<src-bck> ais://<dst-bck>
```

#### 2. Legacy Pod-spec (Still Supported)

The original method using full Kubernetes Pod specification with environment variable substitution:

```bash
# Change Directory (to Desired Sample Transformer)
cd ais-etl/transformers/md5

# Export Environment Variables for Communication Mechanism (& Any Additional Arguments)
export COMMUNICATION_TYPE="hpull://"

# Substitute Environment Variables in YAML Specification
envsubst < pod.yaml > init_spec.yaml

# Initialize ETL on AIStore via CLI
ais etl init spec --from-file init_spec.yaml --name md5-etl-legacy

# Transform objects (inline)
ais etl object md5-etl-legacy ais://<bck-name>/<obj-name>.<ext> -

# Transform bucket-to-bucket
ais etl bucket md5-etl-legacy ais://src-bck ais://dst-bck
```

> **Note**: Most transformers now provide both `etl_spec.yaml` (runtime-spec) and `pod.yaml` (legacy pod-spec) files. The runtime-spec approach is recommended for new deployments.

### Usage w/ AIStore Python SDK

The `YAML` specification files for the sample transformers are provided as [templates](https://github.com/NVIDIA/ais-etl/blob/main/transformers/md5/etl_spec.yaml).

## Contribution

The maintenance of the sample transformers on [DockerHub](https://hub.docker.com/u/aistorage) is managed by the [`ais-etl`](https://github.com/NVIDIA/ais-etl) GitHub repository. 

To contribute, push any changes to sample transformers to the GitHub repository. The existing GitHub workflows will build and push the updated sample transformers to the [DockerHub](https://hub.docker.com/u/aistorage) repostiory.

> For more information, refer to the GitHub workflow files [here](https://github.com/NVIDIA/ais-etl/tree/main/.github/workflows).

## References

- [Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md)
- [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md)
- [AIS-ETL](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md)
