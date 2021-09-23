import os
from setuptools import setup, find_packages

NAME = "ais"
VERSION = "0.0.1"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

cwd = os.path.dirname(os.path.abspath(__file__))
# Read in README.md for our long_description
with open(os.path.join(cwd, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name=NAME,
    version=VERSION,
    description="Client and convenient connectors for PyTorch and TensorFlow to AIStore cluster",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://aiatscale.org',
    author='AIStore Team',
    author_email='ais@exchange.nvidia.com',
    keywords=["aistore", "ai", "object storage", "NVIDIA"],
    license="MIT",
    python_requires='>=3.6.0',
    packages=find_packages(exclude=["ais.tests"]),
    install_requires=['requests'],
    extras_require={
        'pytorch': ['torch', 'torchvision'],
        'tf': ['braceexpand', 'humanfriendly', 'tensorflow', 'tensorflow_addons'],
    },
)
