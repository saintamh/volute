#!/usr/bin/env python3

from pathlib import Path
import setuptools


README_FILE = Path(__file__).parent / "README.md"

LONG_DESCRIPTION = README_FILE.read_text("UTF-8")


setuptools.setup(
    name="volute",
    version="1.0.1",
    description="A Python library for rendering heatmaps to Web Mercator tiles",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
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
