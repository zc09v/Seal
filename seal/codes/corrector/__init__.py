"""Corrector module for Seal library.

This module provides correction strategies for handling validation errors,
including fix prompt generation for LLM re-prompting and default value filling.
"""

from .base import CorrectionStrategy, PromptCorrectionStrategy, DataCorrectionStrategy
from .strategies import DefaultValueStrategy, FixPromptStrategy, TypeConversionStrategy
from .results import CorrectionResult
from .types import CorrectionType

__all__ = [
    'CorrectionStrategy',
    'PromptCorrectionStrategy',
    'DataCorrectionStrategy',
    'DefaultValueStrategy',
    'FixPromptStrategy',
    'TypeConversionStrategy',
    'CorrectionResult',
    'CorrectionType'
]