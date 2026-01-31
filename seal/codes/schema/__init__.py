"""Schema module for Seal library.

This module provides Pydantic-based schema definitions for structured data contracts.
"""

from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional, Union

from .base import SealModel

# Re-export core components for easy access
__all__ = ["SealModel", "BaseModel", "Field", "validator"]