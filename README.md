# AIStore and TensorFlow integration

Experimental project to provide TensorFlow-native AIS dataset (`AisDataset`) and
associated data loaders. The objective is two-fold
* allow Python developers and researchers to run existing TF-based models with almost no modifications
* utilize [AIStore](https://github.com/NVIDIA/aistore) on the backend using the code that looks as follows:

```python
conversions = [Rename(img="jpeg;png"), Decode("img"), Rotate("img"), Resize("img", (224, 244))]
selections = [Select("img"), Select("cls")]

ais = AisDataset(BUCKET_NAME, PROXY_URL, conversions, selections)
train_dataset = ais.load("train-{0..9999}.tar", num-workers=64)
```
