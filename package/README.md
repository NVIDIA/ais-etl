# AIStore Python Client

Experimental project to provide Client and PyTorch as well as TensorFlow connectors to access cluster.
The objective is two-fold:
* allow Python developers and researchers to run existing PyTorch or TF-based models with almost no modifications
* utilize [AIStore](https://github.com/NVIDIA/aistore) on the backend using the code that looks as follows:

  * for PyTorch:
    ```python
    import aistore
    
    train_loader = torch.utils.data.DataLoader( 
        aistore.pytorch.Dataset(
            "http://ais-gateway-url:8080", "lpr-imagenet",
            prefix="train/", transform_id="imagenet-etl",
        ),
        batch_size=args.batch_size, shuffle=True,
        num_workers=args.workers, pin_memory=True,
    )
    ```
    
  * or for TensorFlow:
    ```python
    import aistore
    from aistore.tf import Rename, Decode, Rotate, Resize, Select

    conversions = [
        Rename(img="jpeg;png"), Decode("img"),
        Rotate("img"), Resize("img", (224, 244)),
    ]
    selections = [Select("img"), Select("cls")]
    
    dataset = aistore.tf.Dataset(
        "http://ais-gateway-url:8080", "lpr-imagenet",
        conversions, selections,
    )
    train_dataset = dataset.load("train-{0..9999}.tar", num_workers=64)
    ```

This repository provides for deploying custom ETL containers on AIStore, with subsequent user-defined
extraction, transformation, and loading in parallel, on the fly and/or offline, local to the user data.

## Installation

### Installation Requirements

* Python >= 3.6
* Requests >= 2.0.0

#### Installing the latest release

The latest release of AIStore package is easily installed either via Anaconda (recommended):

```console
$ conda install aistore
```

or via pip:
```console
$ pip install aistore
```

### Manual / Dev install

If you'd like to try our bleeding edge features (and don't mind potentially running into the occasional bug here or there), you can install the latest master directly from GitHub. For a basic install, run:

```console
$ git clone https://github.com/NVIDIA/ais-etl.git
$ cd ais-etl/package
$ pip install -e .
```
To customize the installation, you can also run the following variants of the above:

* `pip install -e .[pytorch]`: Also installs PyTorch dependencies required to use `ais.pytorch` package.
* `pip install -e .[tf]`: Also installs TensorFlow dependencies required to use `ais.tf` package.

## References

Please also see:
* the main [AIStore repository](https://github.com/NVIDIA/aistore),
* [AIStore documentation](https://aiatscale.org/docs), and
* [AIStore and ETL videos](https://github.com/NVIDIA/aistore/blob/master/docs/videos.md).
