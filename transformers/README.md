# Transformers

We have sample transformers `echo`, `md5` and `tar2tf`.

| Transfomer | Description |
| ------ | ------ |
| `echo` | This returns the original data, with an md5 sum in the response headers. |
| `md5` | This returns the md5 sum of the original data as the response. |
| `tar2tf` | This returns the transformed TensorFlow compatible data for the input tar files. |

Each of sample transfomers contains two main files:
- `build.sh` used for building the docker image.
- `pod.yaml` has the spec for the kubernetes pod running this transformer.

## Using sample transformers

### Environment Variables

| Env Variable | Default Value | Description |
| ------ | ------ | ------ |
| `${DOCKER_REGISTRY_IP}` | `localhost:5000` | This refers to the docker hub where we intend to push the docker image of the transformer. |
| `${COMMUNICATION_TYPE}` | `"hpush://"` |This is the mode of communication to be used. For more info read [this](https://github.com/NVIDIA/aistore/blob/master/docs/transformations.md#overview).|


### Terms

`HostMachine` - The place from where the deployment is performed.

### Preqrequisites


1. `kubectl` must be installed on `HostMachine` and connected and correctly configured for `aistore` kubernetes network.
2. `docker` must be installed on the `HostMachine`.

**Steps:**

1. We **must** set the `${DOCKER_REGISTRY_URL}` and `${COMMUNICATION_TYPE}` environment variables first with appropriate values.
2. `eval "echo \"$(cat pod.yaml)\"" > pod_config.yaml # Substitutes the environment variables used`
3. `./build.sh # This builds the docker image`
4. `docker push <IMAGE_URL> # <IMAGE_URL> can be obtained post the build step`
5. `ais transform init pod_config.yaml`
