"""Correction strategies for Seal library.

This module contains various correction strategies that handle validation errors
and provide different correction mechanisms.
"""

from .default_value_strategy import DefaultValueStrategy
from .fix_prompt_strategy import FixPromptStrategy
from .type_conversion_strategy import TypeConversionStrategy

__all__ = [
    'DefaultValueStrategy',
    'FixPromptStrategy',
    'TypeConversionStrategy'
]