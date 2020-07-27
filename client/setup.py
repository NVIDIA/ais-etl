# coding: utf-8
"""
    AIS-TAR2TF

    Experimental project to provide TensorFlow-native AIS dataset (AisDataset) and associated data loaders.  # noqa: E501
"""

from setuptools import setup, find_packages  # noqa: H301

NAME = "ais_tar2tf"
VERSION = "0.2.0"
# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

setup(
    name=NAME,
    version=VERSION,
    description="AIS_TAR2TF",
    author="NVIDIA-AIS_TAR2TF",
    author_email="aisdev@exchange.nvidia.com",
    url="",
    keywords=["AIS", "ais_tar2tf", "NVIDIA"],
    packages=find_packages(exclude=["examples", "docs", "deploy"]),
    include_package_data=True,
    license="MIT",
    long_description="""\
    Experimental project to provide TensorFlow-native AIS dataset (AisDataset) and associated data loaders  # noqa: E501
    """
)
