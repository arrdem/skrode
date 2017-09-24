#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="skrode",
    version="0.0.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
)
