"""
Validator module for Seal library.

This module provides validation capabilities for structured data against Pydantic models.
"""

from .errors import ValidationError, ValidationResult
from .validator import Validator, ValidationRule

__all__ = ['Validator', 'ValidationResult', 'ValidationError', 'ValidationRule']