"""Type definitions for LLM Adapter module."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMResponse:
    """Standardized LLM response structure."""
    
    content: str
    """The text content returned by the LLM."""
    
    model: str
    """The name of the model used for generation."""
    
    usage: Optional[dict[str, int]] = None
    """Token usage information if available."""
    
    finish_reason: Optional[str] = None
    """The reason why the generation finished."""
    
    raw_response: Optional[Any] = None
    """The raw response object for debugging purposes."""