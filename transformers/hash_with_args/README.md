# Hash-With-Args Transformer

A simple hash transformer that processes objects (bytes) by extracting ETL arguments from an inline transform request.

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the **Hash-With-Args transformer** using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md).

There are **two** ways to start this transformer:

1. **Runtime-spec (recommended)** – a compact YAML that lists only the image, command, and (optionally) the communication type, argument, timeouts, runtime etc.
2. **Legacy pod-spec** – the original full Kubernetes Pod specification plus `envsubst`.

---
#### 1. Runtime-spec (recommended)

Create a YAML file (e.g. `etl_spec.yaml`):

```yaml
# etl_spec.yaml
name: hwa-etl
runtime:
  image: aistorage/transformer_hash_with_args:latest
  env:
    - name: SEED_DEFAULT
      value: "0"
# Other optional values
```

The `SEED_DEFAULT` environment variable will be used to compute the hash only if `--etl-args` is not provided in the request.

> For details on communication modes see the [AIStore ETL docs](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms) for details on communication types.

#### Initialize the ETL

```bash
# create the ETL
ais etl init spec --from-file etl_spec.yaml --name hwa-etl
```

To customize fields (resources, env, timeouts, etc.) see the sample [etl_spec.yaml](transformers/hash_with_args/etl_spec.yaml).

#### Transform objects (inline or bucket-to-bucket)

```bash
# Inline transform with default seed (0)
ais etl object hwa-etl ais://<src-bck>/<obj> -

# Inline transform with custom seed 42 (note the --etl-args flag)
ais etl object hwa-etl ais://<src-bck>/<obj> - --etl-args 42

# Bucket-to-bucket transform with default seed (0)
ais etl bucket hwa-etl ais://<src-bck> ais://<dst-bck>
```
The output is the hexadecimal XXHash64 digest of the original object bytes.

---
#### 2. Legacy pod-spec (still supported)

```!bash
$ cd transformers/hash_with_args

$ # Mention communication type between target and container
$ export COMMUNICATION_TYPE=hpull://
$ # Mention communication type between target and container
$ export COMMUNICATION_TYPE=hpull://

# Substitute env variables in spec file
$ envsubst < pod.yaml > init_spec.yaml

$ # Initialize ETL
$ ais etl init spec --from-file etl_spec.yaml

$ # Put an object
$ ais object put <your-file> ais://<bck-name>

$ # Transform and retrieve objects from the bucket using this ETL with arguments
$ ais etl object hwa-etl-legacy ais://<bck-name>/<your-obj> - --etl-args 100000
```