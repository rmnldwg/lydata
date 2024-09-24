"""Library for handling lymphatic involvement data."""

import logging

import lydata._version as _version

__author__ = "Roman Ludwig"
__email__ = "roman.ludwig@usz.ch"
__uri__ = "https://github.com/rmnldwg/lydata"
_repo = __uri__.replace("https://github.com/", "")
__version__ = _version.__version__

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.WARNING)
