# Keras Transformer - Image Data Augmentation and Preprocessing

The Keras Transformer is a powerful tool designed for image data preprocessing and data augmentation. Leveraging the Keras `ImageDataGenerator` class, this transformer allows users to define transformations by providing a JSON string with parameter-value pairs. The following parameters are supported and tested:

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

The transformer supports both `hpull` and `hpush` communication mechanisms for seamless integration.

**Please Note:** This transformer utilizes the [`FastAPI`](https://fastapi.tiangolo.com/) framework alongside the [`Gunicorn`](https://gunicorn.org/) + [Uvicorn](https://www.uvicorn.org/) combination as its web server. Alternate implementations of the same functionality are provided using [`Flask`](https://flask.palletsprojects.com/en/2.3.x/) and [`Gunicorn`](https://gunicorn.org/) within the [`flask-gunicorn`](/flask-gunicorn) directory. Additionally, there's a version that employs a multithreaded HTTP server, which can be found in the [`http-multithreaded-server`](/http-multithreaded-server/) folder.

> For more information on communication mechanisms, please refer to [this link](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

## Parameters
Only two parameters need to be updated in the `pod.yaml` file.

| Argument    | Description                                                           | Default Value |
| ----------- | --------------------------------------------------------------------- | ------------- |
| `TRANSFORM`      | Specify a JSON string with operations to be performed | ``     |
| `FORMAT`| To process/store images in which image format (PNG, JPEG,etc)           | `JPEG`          |

Please ensure to adjust these parameters according to your specific requirements.

## ETL Args - Runtime Transform Parameters

In addition to the default `TRANSFORM` environment variable, users can override transformation parameters at runtime by passing **ETL args** when calling the transformation. This allows for dynamic, per-request customization of image transformations without requiring ETL reinitialization.

### How ETL Args Work

- **Format**: JSON string containing transformation parameters
- **Encoding**: ETL args are automatically URL-decoded by the server
- **Precedence**: ETL args override the default `TRANSFORM` environment variable for that specific request
- **Fallback**: If ETL args are invalid or missing, the transformation falls back to the default `TRANSFORM` parameters

### Supported ETL Args Parameters

ETL args support the same parameters as the `TRANSFORM` environment variable (Keras ImageDataGenerator parameters):

| Parameter                | Type    | Description                                             | Example Values        |
|-------------------------|---------|---------------------------------------------------------|-----------------------|
| `rotation_range`        | Float   | Range for random rotations (in degrees)                | `40`, `90`, `180`     |
| `width_shift_range`     | Float   | Range for random horizontal shifts                      | `0.2`, `0.3`          |
| `height_shift_range`    | Float   | Range for random vertical shifts                        | `0.2`, `0.3`          |
| `shear_range`           | Float   | Range for random shear transformations                  | `0.2`, `0.5`          |
| `zoom_range`            | Float   | Range for random zoom                                   | `0.2`, `0.5`          |
| `horizontal_flip`       | Boolean | Enable random horizontal flips                          | `true`, `false`       |
| `fill_mode`             | String  | Fill mode ("nearest", "constant", "reflect", "wrap")    | `"nearest"`, `"constant"` |

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