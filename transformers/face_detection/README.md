# Face Detection Using Single Shot Multibox Detector (SSD) Model

This document outlines the process of utilizing the `Single Shot MultiBox Detector (SSD)` model for face detection in images. The SSD model predicts and places bounding boxes over faces in an image. For further reading on the SSD model, visit the [research paper](https://arxiv.org/abs/1512.02325).

![output](sample/output_face_detection.png)

> **Note**: Due to size constraints, the model's weights and architecture are not included in this directory. They are pre-loaded in the transformer's Docker [image](https://hub.docker.com/r/aistorage/transformer_face_detection).

## Image Format Specification

The image formats (`jpeg`, `png`, etc.) for processing or storage are defined by the `FORMAT` environment variable in [`etl_spec.yaml`](etl_spec.yaml).

## Transformer Communication Mechanisms

The transformer is compatible with `hpull` and `hpush` for seamless integration. Detailed information about these communication mechanisms can be found [here](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

## Web Server Framework

The transformer employs the [`FastAPI`](https://fastapi.tiangolo.com/) framework, and uses [`Gunicorn`](https://gunicorn.org/) and [Uvicorn](https://www.uvicorn.org/) as the web server combination.

## Configurable Parameters

Adjust the following parameters in `etl_spec.yaml` as needed:

| Argument   | Description                                                         | Default Value |
|------------|---------------------------------------------------------------------|---------------|
| `FORMAT`   | Image format for processing/storing (png, jpeg, etc.)                | "jpeg"        |
| `FILE_FORMAT` | Configure as "tar" for processing datasets in the webdataset format or for handling batches of images packaged in a tarball   | ""            |

### Setting Up the Face Detection Transformer with AIStore CLI

To initialize the `Face Detection Transformer` using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md), follow these steps:

```bash
# Navigate to the transformer directory
cd transformers/face_detection

# Edit FORMAT and FILE_FORMAT in etl_spec.yaml as needed

# Initialize the ETL process
ais etl init -f etl_spec.yaml --name <etl-name> --comm-type hpush://

# Use the ETL for transforming and retrieving objects
# For inline transformation
ais etl object <etl-name> ais://src/<image-name>.JPEG dst.JPEG

# For offline (bucket-to-bucket) transformation
ais etl bucket <etl-name> ais://src-bck ais://dst-bck --ext="{jpg:jpg}"

# or, if using webdataset style format
# ais etl bucket <etl-name> ais://src-bck ais://dst-bck --ext="{tar:tar}"
```
