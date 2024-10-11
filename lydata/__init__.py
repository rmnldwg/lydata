"""Library for handling lymphatic involvement data."""

import logging

import lydata._version as _version
from lydata.accessor import C, Q
from lydata.loader import (
    available_datasets,
    join_datasets,
    load_datasets,
)
from lydata.validator import validate_datasets

__author__ = "Roman Ludwig"
__email__ = "roman.ludwig@usz.ch"
__uri__ = "https://github.com/rmnldwg/lydata"
__version__ = _version.__version__

__all__ = [
    "accessor",
    "Q",
    "C",
    "available_datasets",
    "join_datasets",
    "load_datasets",
    "validate_datasets",
]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.WARNING)
