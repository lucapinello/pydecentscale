# -*- coding: utf-8 -*-
# Copyright (c) 2021 Luca Pinello
# GPLv3 license


import os
from setuptools import setup
from setuptools import find_packages

import re

version = re.search(
    	'^__version__\s*=\s*"(.*)"',
    	open('pydecentscale/__init__.py').read(),
    	re.M
    	).group(1)

setup(
    name='pydecentscale',
    version=version,
    description='A Python module to interact with the Decent Scale via bluetooth (BLE)',
    url='https://github.com/lucapinello/pydecentscale',
    author='Luca Pinello',
    license='GPLv3',
    packages=find_packages(),
    install_requires=[
        'bleak','asyncio','nest_asyncio'     
    ]
)
