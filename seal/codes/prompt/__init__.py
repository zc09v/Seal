"""Prompt module for Seal library.

This module provides prompt building capabilities for converting Pydantic models 
into LLM-friendly format instructions.
"""

from .builder import PromptBuilder, build_format_instructions

__all__ = ["PromptBuilder", "build_format_instructions"]