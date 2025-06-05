# Echo Transformer

A simple echo transformer that takes objects (bytes) and simply echoes or repeats those bytes back as output. It's a simple and straightforward way to demonstrate or test the functionality of your container pod. An echo transformer might be used for debugging, understanding how data flows through a system, or verifying that certain processes are functioning as expected.

The transformer supports both `hpull` and `hpush` communication mechanisms for seamless integration.


> For more information on communication mechanisms, please refer to [this link](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the `hello-world-transformer` with using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md):

```!bash
$ cd transformers/hello_world

$ # Initialize ETL
$ ais etl init spec --from-file etl_spec.yaml

$ # Transform and retrieve objects from the bucket using this ETL
$ # For inline transformation
$ ais etl object <etl-name> ais://<bck-name>/<obj-name>.<ext> -

$ # Or, for offline (bucket-to-bucket) transformation
$ ais etl bucket <etl-name> ais://src-bck ais://dst-bck 
```