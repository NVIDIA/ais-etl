# Transformers

We have sample transformers `echo`, `md5` and `tar2tf`.

| Transformer | Language | Description |
| ---------- | -------- | ----------- |
| `echo` | `python:3.8.5` | This returns the original data, with an md5 sum in the response headers. |
| `go-echo` | `golang:1.16` | This returns the original data, with an md5 sum in the response headers. |
| `hello_world` | `python:3.8.5` | This always returns `Hello World!` string on any request. |
| `md5` | `python:3.8.5` | This returns the md5 sum of the original data as the response. |
| `tar2tf` | `golang:1.16` | This returns the transformed TensorFlow compatible data for the input tar files. |

Each of sample transformers contains three main files:
- `Dockerfile` - contains description of Docker image.
- `pod.yaml` - contains the spec for the K8s Pod running this transformer.
- `Makefile` - used for building and pushing Docker image.

## Using sample transformers

### Environment Variables

| Env Variable | Default Value | Description |
| ------ | ------ | ------ |
| `${COMMUNICATION_TYPE}` | `"hpush://"` | This is the mode of communication to be used. For more info read [this](https://github.com/NVIDIA/aistore/blob/master/docs/transformations.md#overview). |

### Terms

`HostMachine` - The place from where the deployment is performed.

### Prerequisites

1. `kubectl` must be installed on `HostMachine` and connected and correctly configured for `aistore` kubernetes network.
2. `docker` must be installed on the `HostMachine`.

**Steps:**

1. We **must** set the `${COMMUNICATION_TYPE}` environment variable first with appropriate value.
2. `eval "echo \"$(cat pod.yaml)\"" > pod_config.yaml` - substitutes the environment variables
3. `make build` - builds the Docker image
4. `docker push <IMAGE_URL>` - <IMAGE_URL> can be obtained post the build step
5. `ais transform init pod_config.yaml`
