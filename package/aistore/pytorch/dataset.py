from aistore.client import Bck, Client

from collections import defaultdict
import io
import os

import torch.utils.data
from torchvision import transforms
from PIL import Image


def default_loader(object_name, data):
    ext = os.path.splitext(object_name)[1]
    if ext == ".jpg":
        img = Image.open(io.BytesIO(data))
        return transforms.ToTensor()(img.convert("RGB"))
    elif ext == ".cls":
        return int(data)
    else:
        return data


class Dataset(torch.utils.data.Dataset):
    def __init__(
        self,
        url: str,
        bck: Bck,
        prefix="",
        loader=None,
        transform_id=None,
        transform_filter=None,
    ):
        self.loader = loader
        if self.loader is None:
            self.loader = default_loader
        self.transform_id = transform_id
        self.transform_filter = transform_filter

        self.bck = bck
        self.client = Client(url)
        objects = self.client.list_objects(self.bck, prefix=prefix, sort=True)
        records = defaultdict(list)
        for obj_info in objects:
            base_name = os.path.splitext(obj_info["name"])[0]
            records[base_name].append(obj_info["name"])

        self.samples = list(records.values())

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index: int):
        object_names = self.samples[index]
        transform_id = ""

        sample = []
        for object_name in object_names:
            if self.transform_id is not None:
                if self.transform_filter is not None:
                    if self.transform_filter(object_name):
                        transform_id = self.transform_id
                else:
                    transform_id = self.transform_id

            sample.append(
                self.loader(
                    object_name,
                    self.client.get_object(
                        self.bck, object_name, transform_id=transform_id
                    ),
                )
            )

        return tuple(sample)
