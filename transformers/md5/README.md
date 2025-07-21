# MD5 Transformer

A simple transformer that calculates the **MD5 checksum** of each incoming object and returns the 32-character hexadecimal digest. Useful for verifying data integrity or learning how ETL data flows through AIStore.

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the **MD5 transformer** using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md).

There are **two** ways to start this transformer:

1. **Runtime-spec (recommended)** – a compact YAML that lists only the image, command, and (optionally) the communication type, argument, timeouts, runtime etc.
2. **Legacy pod-spec** – the original full Kubernetes Pod specification plus `envsubst`.

---

#### 1. Runtime-spec (recommended)

Create a YAML file (e.g. `etl_spec.yaml`):

```yaml
# etl_spec.yaml
name: md5-etl
runtime:
  image: aistorage/transformer_md5:latest
# Other optional values
```
> For details on communication modes see the [AIStore ETL docs](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

#### Initialize the ETL

```bash
# create the ETL
ais etl init spec --from-file etl_spec.yaml md5-etl
```

This initializes the ETL with default settings. To customize, see the sample [etl_spec.yaml](Dockerfile) for all available fields.

#### Transform objects (inline or bucket-to-bucket)

```bash
# Inline transform (prints MD5 digest)
ais etl object md5-etl ais://<src-bck>/<obj> -

# Bucket-to-bucket transform (stores MD5 digests as objects)
ais etl bucket md5-etl ais://<src-bck> ais://<dst-bck>
```

---

#### 2. Legacy pod-spec (still supported)

```!bash
$ cd transformers/md5

$ # Mention communication type between target and container
$ export COMMUNICATION_TYPE=hpull://

# Substitute env variables in the full pod spec
$ envsubst < pod.yaml > init_spec.yaml

$ # Initialize ETL
$ ais etl init spec --from-file init_spec.yaml --name md5-etl-legacy

$ # Transform and retrieve objects from the bucket using this ETL
$ ais etl object md5-etl-legacy ais://<bck-name>/<obj-name>.<ext> -

$ # Or, for offline (bucket-to-bucket) transformation
$ ais etl bucket md5-etl-legacy ais://src-bck ais://dst-bck 
```

### Quick test from scratch

If you don't already have buckets and objects to transform, create them on the fly and verify the transformer works:

```bash
# 1) Create a bucket and upload a text object
ais bucket create ais://md5_demo
echo "hello" | ais put - ais://md5_demo/hello.txt

# 2) Run the transformer inline (prints MD5 of "hello")
ais etl object md5-etl ais://md5_demo/hello.txt -
# → 5d41402abc4b2a76b9719d911017c592

# 3) (Optional) Transform an entire bucket to a new one
ais bucket create ais://md5_demo_out
ais etl bucket md5-etl ais://md5_demo ais://md5_demo_out
```

The `md5-etl` transformer returns an MD5 digest for any input; the example above prints the digest of `hello`, confirming the ETL is operational. 