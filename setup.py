#!/usr/pycrosskit/env python3

import os

from setuptools import setup, find_packages

# get key package details from pycrosskit/__version__.py
about = {}  # type: ignore
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "abst", "__version__.py")) as f:
    exec(f.read(), about)

# load the README file and use it as the long_description for PyPI
with open("README.md", "r") as f:
    readme = f.read()

setup(
    name=about["__title__"],
    description=about["__description__"],
    long_description=readme,
    long_description_content_type="text/markdown",
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.7,<4",
    install_requires=["click", "rich", "inquirerpy", "oci==2.150.0", "lastversion",
                      "semantic_version", "pyperclip",
                      "bext", "deepmerge~=2.0"],
    extras_require={
        "dev": ["black==22.*"],
    },
    license=about["__license__"],
    zip_safe=True,
    entry_points={
        "console_scripts": ["abst=abst.main:main"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="Auto OCI Bastion",
)
