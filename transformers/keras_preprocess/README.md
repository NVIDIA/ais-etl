# Keras Transformer - Image Data Augmentation and Preprocessing

The Keras Transformer is a powerful tool designed for image data preprocessing and data augmentation. Leveraging the `apply_transform` function from Keras (TensorFlow), this transformer allows users to define transformations by providing a JSON string with parameter-value pairs. Currently, the following parameters are supported:

| Parameter                | Description                                             |
|-------------------------|---------------------------------------------------------|
| 'theta'                 | Rotation angle in degrees.                              |
| 'tx'                     | Shift in the x direction.                                 |
| 'ty'                     | Shift in the y direction.                                 |
| 'shear'                 | Shear angle in degrees.                                    |
| 'zx'                     | Zoom in the x direction.                                  |
| 'zy'                     | Zoom in the y direction.                                  |
| 'flip_horizontal'    | Boolean. Enable horizontal flip.                          |
| 'flip_vertical'        | Boolean. Enable vertical flip.                              |
| 'channel_shift_intensity' | Float. Channel shift intensity.                          |
| 'brightness'            | Float. Brightness shift intensity.                          |

The image format (JPEG, PNG, etc.) of the images to be processed or stored is specified in the `spec.yaml`.

The transformer supports both `hpull`, `hpush` and `hrev` communication mechanisms for seamless integration.

**Please Note:** This transformer utilizes the [`FastAPI`](https://fastapi.tiangolo.com/) framework alongside the [`Gunicorn`](https://gunicorn.org/) + [Uvicorn](https://www.uvicorn.org/) combination as its web server. Alternate implementations of the same functionality are provided using [`Flask`](https://flask.palletsprojects.com/en/2.3.x/) and [`Gunicorn`](https://gunicorn.org/) within the [`flask-gunicorn`](/flask-gunicorn) directory. Additionally, there's a version that employs a multithreaded HTTP server, which can be found in the [`http-multithreaded-server`](/http-multithreaded-server/) folder.

> For more information on communication mechanisms, please refer to [this link](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

## Parameters
Only two parameters need to be updated in the `pod.yaml` file.

| Argument    | Description                                                           | Default Value |
| ----------- | --------------------------------------------------------------------- | ------------- |
| `TRANSFORM`      | Specify a JSON string with operations to be performed | ``     |
| `FORMAT`| To process/store images in which image format (PNG, JPEG,etc)           | `JPEG`          |

Please ensure to adjust these parameters according to your specific requirements.

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the `Keras Transformer` with using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md):

```!bash
$ cd transformers/keras_transformer

$ # Set values for FORMAT and TRANSFORM
$ export FORMAT="JPEG"
$ export TRANSFORM='{"theta":40, "brightness":0.8, "zx":0.9, "zy":0.9}'

$ # Mention communication type b/w target and container
$ export COMMUNICATION_TYPE = 'hpull://'

# Substitute env variables in spec file
$ envsubst < pod.yaml > init_spec.yaml

$ # Initialize ETL
$ ais etl init spec --from-file init_spec.yaml --name <etl-name>

$ # Transform and retrieve objects from the bucket using this ETL
$ # For inline transformation
$ ais etl object <etl-name> ais://src/<image-name>.JPEG dst.JPEG
$ # Or, for offline (bucket-to-bucket) transformation
$ ais etl bucket <etl-name> ais://src-bck ais://dst-bck --ext="{JPEG:JPEG}" 
```