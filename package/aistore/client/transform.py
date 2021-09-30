import base64
from abc import ABC, abstractmethod

import cloudpickle
import pip._internal.utils.misc as pip

from .api import Client
from .const import ETL_IO_COMM_TYPE, ETL_PUSH_COMM_TYPE
from .msg import Bck, BuildETL

CLOUD_TEMPLATE = """
import pickle
import base64

_base64code = base64.b64decode('{}')
transform = pickle.loads(_base64code)
"""

WD_TEMPLATE = """
import os
os.environ['OPENBLAS_NUM_THREADS'] = '4'

import webdataset as wds
import pickle
import base64


dataset = wds.WebDataset("-").decode('{decoder}')
_base64code = base64.b64decode('{str_func}')
transform = pickle.loads(_base64code)

with wds.TarWriter("-") as sink:
    for sample in dataset:
        sample = transform(sample)
        sink.write(sample)
"""


class BaseTransform(ABC):
    def __init__(
        self,
        client: Client,
        transform_func,
        transform_name: str = "",
        comm_type: str = ETL_PUSH_COMM_TYPE,
        verbose=False,
    ):
        self.client = client
        self.transform_func = transform_func  # ETL Container
        self.name = transform_name
        self._is_ready = False
        self.verbose = verbose
        self.comm_type = comm_type
        assert self.transform_func != None and callable(transform_func)
        assert comm_type == ETL_PUSH_COMM_TYPE or comm_type == ETL_IO_COMM_TYPE

    @abstractmethod
    def _base64_code(self):
        pass

    def _base64_deps(self):
        installed_packages = pip.get_installed_distributions()
        installed_packages_list = [
            f"{i.key}=={i.version}"
            for i in installed_packages
            if i.version != "0.0.0"
        ]

        # TODO: should be installed in all runtimes
        cloud_pickle_exist = False
        for deps in installed_packages:
            if deps.key == "cloudpickle":
                cloud_pickle_exist = True

        if not cloud_pickle_exist:
            installed_packages_list.append("cloudpickle==2.0.0")
        deps = "\n".join(installed_packages_list).encode("utf-8")
        return base64.b64encode(deps).decode("utf-8")

    def init(self):
        if self.verbose:
            print("Initializing ETL...")

        build_msg = BuildETL(
            self._base64_code(),
            self._base64_deps(),
            self.comm_type,
            id=self.name,
        )
        # TODO: error handling
        self.name = self.client.etl_build(build_msg)
        self._is_ready = True

        if self.verbose:
            print(f"ETL {self.name} successfully initialized")

    def exec(self, from_bck: Bck, to_bck: Bck) -> str:
        if not self._is_ready:
            self.init()
        return self.client.transform_bucket(from_bck, to_bck, self.name)

    def get(self, bck: Bck, obj: str) -> bytes:
        if not self._is_ready:
            self.init()
        return self.client.get_object(bck, obj, transform_id=self.name)

    @property
    def uuid(self):
        if not self._is_ready:
            self.init()
        return self.name


class BytesTransform(BaseTransform):
    def __init__(
        self,
        client: Client,
        transform_func,
        transform_name="",
        verbose=False,
    ):
        super().__init__(
            client,
            transform_func,
            transform_name=transform_name,
            comm_type=ETL_PUSH_COMM_TYPE,
            verbose=verbose,
        )

    def _base64_code(self):
        str_func = base64.b64encode(
            cloudpickle.dumps(self.transform_func)
        ).decode("utf-8")
        func_bytes = CLOUD_TEMPLATE.format(str_func).encode("utf-8")
        return base64.b64encode(func_bytes).decode("utf-8")


class WDTransform(BaseTransform):
    def __init__(
        self,
        client: Client,
        transform_func,
        transform_name="",
        wd_decoder="pil",
        verbose=False,
    ):
        super().__init__(
            client,
            transform_func,
            transform_name=transform_name,
            comm_type=ETL_IO_COMM_TYPE,
            verbose=verbose,
        )
        self.wd_decoder = wd_decoder

    def _base64_code(self):
        str_func = base64.b64encode(
            cloudpickle.dumps(self.transform_func)
        ).decode("utf-8")
        func_bytes = WD_TEMPLATE.format(
            str_func=str_func, decoder=self.wd_decoder
        ).encode("utf-8")
        return base64.b64encode(func_bytes).decode("utf-8")
