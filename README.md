# AIStore TensorFlow Integration

Experimental project to provide TensorFlow-native AIS dataset (`AisDataset`) and
associated data loaders. The objective is two-fold:
* allow Python developers and researchers to run existing TF-based models with almost no modifications
* utilize [AIStore](https://github.com/NVIDIA/aistore) on the backend using the code that looks as follows:

```python
conversions = [Rename(img="jpeg;png"), Decode("img"), Rotate("img"), Resize("img", (224, 244))]
selections = [Select("img"), Select("cls")]

ais = AisDataset(lpr-imagenet, http://ais-gateway-url, conversions, selections)
train_dataset = ais.load("train-{0..9999}.tar", num-workers=64)
```

This repository provides for deploying custom ETL containers on AIStore, with subsequent user-defined
extraction, transformation, and loading in parallel, on the fly and/or offline, local to the user data.

Please also see the main [AIStore repository](https://github.com/NVIDIA/aistore),
[AIStore documentation](https://nvidia.github.io/aistore/), and
[AIStore and ETL videos](https://github.com/NVIDIA/aistore/blob/master/docs/videos.md).
