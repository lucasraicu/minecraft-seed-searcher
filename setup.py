from setuptools import setup

setup(cffi_modules=["native/build.py:ffibuilder", "native/blueprint_build.py:ffibuilder"])
