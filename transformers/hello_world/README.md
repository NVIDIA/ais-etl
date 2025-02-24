# Simple Hello World Transformer

A simple hello world transformer that reads objects stored in AIStore and returns "Hello World" in bytes for every object stored.

The transformer supports both `hpull`, `hpush` and `hrev` communication mechanisms for seamless integration.

> **Note:** This transformer is using [`FastAPI`](https://fastapi.tiangolo.com/) as framework and [`Gunicorn`](https://gunicorn.org/) + [Uvicorn](https://www.uvicorn.org/) as webserver, multithreaded HTTP server for the same implmentation under [`http-multithreaded-server`](/http-multithreaded-server/) folder.

> For more information on communication mechanisms, please refer to [this link](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the `hello-world-transformer` with using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md):

```!bash
$ cd transformers/hello_world

$ # Mention communication type b/w target and container
$ export COMMUNICATION_TYPE = 'hpull://'

# Substitute env variables in spec file
$ envsubst < pod.yaml > init_spec.yaml

$ # Initialize ETL
$ ais etl init spec --from-file init_spec.yaml --name <etl-name>

$ # Transform and retrieve objects from the bucket using this ETL
$ # For inline transformation
$ ais etl object <etl-name> ais://<bck-name>/<obj-name>.<ext> -

$ # Or, for offline (bucket-to-bucket) transformation
$ ais etl bucket <etl-name> ais://src-bck ais://dst-bck 
```