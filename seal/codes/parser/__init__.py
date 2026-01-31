"""Parser module for Seal library."""

from .json_parser import JsonParser
from .errors import JsonParseError

__all__ = ["JsonParser", "JsonParseError"]