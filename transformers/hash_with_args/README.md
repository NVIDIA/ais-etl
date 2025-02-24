# Hash with Args Transformer

A simple hash transformer that processes objects (bytes) by extracting ETL arguments from an inline transform request and using it as a seed value to compute a seeded hash. This example demonstrates how to pass custom metadata for each individual object through an ETL inline transform and utilize it within your pod.

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the `transformer-hash-with-args` with using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md):

```!bash
$ cd transformers/hash_with_args

$ # Mention communication type b/w target and container
$ export COMMUNICATION_TYPE='hpull://'

# Substitute env variables in spec file
$ envsubst < pod.yaml > init_spec.yaml

$ # Initialize ETL
$ ais etl init spec --from-file init_spec.yaml --name <etl-name> --comm-type "hpull://"

$ # Put an object
$ ais object put <your-file> ais://<bck-name>

$ # Transform and retrieve objects from the bucket using this ETL with arguments
$ curl -L -X GET "${AIS_ENDPOINT}/v1/objects/<bck-name>/<your-file>?etl_name=<etl-name>&etl_meta=100000"
```