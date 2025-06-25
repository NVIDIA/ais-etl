# Simple Hello World Transformer

A simple hello world transformer that reads objects stored in AIStore and returns "Hello World" in bytes for every object stored.

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the `hello-world-transformer` using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md):
There are **two** ways to start this transformer:

1. **Runtime-spec (recommended)** – a compact YAML that lists only the image, command, and (optionally) the communication type, argument, timeouts, runtime etc.
2. **Legacy pod-spec** – the original full Kubernetes Pod specification plus `envsubst`.

---

#### 1. Runtime-spec (recommended)

#### Initialize the ETL

```bash
# Navigate to the hello_world directory
cd transformers/hello_world

# Create the ETL
ais etl init -f etl_spec.yaml
```

This initializes the ETL with default settings. To customize, see the sample [etl_spec.yaml](./etl_spec.yaml) for all available fields.
> For more information on communication mechanisms, please refer to [this link](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

#### Transform objects (inline or bucket-to-bucket)

```bash
# Inline transform (prints "Hello World")
ais etl object hello-world-etl ais://<src-bck>/<obj> -

# Bucket-to-bucket transform
ais etl bucket hello-world-etl ais://<src-bck> ais://<dst-bck>
```

---
#### 2. Legacy pod-spec (still supported)

```!bash
$ cd transformers/hello_world

$ # Initialize ETL
$ ais etl init spec --from-file init_spec.yaml --name hello-world-etl

$ # Transform and retrieve objects from the bucket using this ETL
$ # For inline transformation
$ ais etl object <etl-name> ais://<bck-name>/<obj-name>.<ext> -

$ # Or, for offline (bucket-to-bucket) transformation
$ ais etl bucket <etl-name> ais://src-bck ais://dst-bck 
```

### Quick test from scratch

If you don't already have buckets and objects to transform, create them on the fly and verify the transformer works:

```bash
# 1) Create a bucket and upload a text object
ais bucket create ais://demo
echo "sample" | ais put - ais://demo/hello.txt

# 2) Run the transformer inline (prints "Hello World")
ais etl object hello-world-etl ais://demo/hello.txt -

# 3) Transform an entire bucket to a new one
ais bucket create ais://demo-out
ais etl bucket hello-world-etl ais://demo ais://demo-out
```
