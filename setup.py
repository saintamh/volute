#!/usr/bin/env python3

import setuptools


setuptools.setup(
    name="volute",
    version="1.0.0",
    url="https://github.com/saintamh/volute",
    author="Hervé Saint-Amand",
    packages=["volute"],
    package_data={"volute": ["py.typed"]},
    install_requires=[
        "haversine~=2.0",
        "mercantile~=1.0",
        "numpy~=1.13",
        "Pillow~=9.0",
    ],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    zip_safe=False,  # https://mypy.readthedocs.io/en/latest/installed_packages.html#creating-pep-561-compatible-packages
)
