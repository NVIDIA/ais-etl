# Echo Transformer

A simple echo transformer that takes objects (bytes) and simply echoes or repeats those bytes back as output. It's a simple and straightforward way to demonstrate or test the functionality of your container pod. An echo transformer might be used for debugging, understanding how data flows through a system, or verifying that certain processes are functioning as expected.

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the **echo transformer** using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md).

There are **two** ways to start this transformer:

1. **Runtime-spec (recommended)** – a compact YAML that lists only the image, command, and (optionally) the communication type, argument, timeouts, runtime etc.
2. **Legacy pod-spec** – the original full Kubernetes Pod specification plus `envsubst`.

---

#### 1. Runtime-spec (recommended)

Create a YAML file (e.g. `etl_spec.yaml`):

```yaml
# etl_spec.yaml
name: echo-etl
runtime:
  image: aistorage/transformer_echo:latest
# Other optional values
```

> For more information on communication mechanisms, please refer to [this link](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

#### Initialize the ETL

```bash
# create the ETL
ais etl init spec --from-file etl_spec.yaml --name echo-etl
```

This initializes the ETL with default settings. To customize, see the sample [etl_spec.yaml](transformers/echo/etl_spec.yaml) for all available fields.

#### Transform objects (inline or bucket-to-bucket)

```bash
# Inline transform (prints object content)
ais etl object echo-etl ais://<src-bck>/<obj> -

# Bucket-to-bucket transform (copies objects unchanged)
ais etl bucket echo-etl ais://<src-bck> ais://<dst-bck>
```

---

#### 2. Legacy pod-spec (still supported)

```!bash
$ cd transformers/echo

$ # Mention communication type between target and container
$ export COMMUNICATION_TYPE=hpull://

# Substitute env variables in the full pod spec
$ envsubst < pod.yaml > init_spec.yaml

$ # Initialize ETL
$ ais etl init spec --from-file init_spec.yaml --name echo-etl-legacy

$ # Transform and retrieve objects from the bucket using this ETL
$ ais etl object echo-etl-legacy ais://<bck-name>/<obj-name>.<ext> -

$ # Or, for offline (bucket-to-bucket) transformation
$ ais etl bucket echo-etl-legacy ais://src-bck ais://dst-bck 
```

### Quick test from scratch

If you don't already have buckets and objects to transform, create them on the fly and verify the transformer works:

```bash
# 1) Create a bucket and upload a text object
ais bucket create ais://echo_demo
echo "sample text" | ais put - ais://echo_demo/hello.txt

# 2) Run the transformer inline (prints "sample text")
ais etl object echo-etl ais://echo_demo/hello.txt -

# 3) (Optional) Transform an entire bucket to a new one
ais bucket create ais://echo_demo_out
ais etl bucket echo-etl ais://echo_demo ais://echo_demo_out
```

The `echo-etl` transformer returns the object data unchanged, so the inline test prints the original content, confirming the ETL is operational.