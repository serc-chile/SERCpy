# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 13:51:50 2026

@author: Adrian Riebel Brummer
"""

import sys
from . import demand_profile
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("sercpy")  # the distribution name from pyproject.toml's [project] name
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "unknown"