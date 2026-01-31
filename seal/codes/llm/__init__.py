"""LLM Adapter module for Seal library."""

from .base import LLMAdapter
from .types import LLMResponse
from .errors import (
    LLMError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConfigurationError,
)
from .adapters.deepseek import DeepSeekAIAdapter, DeepSeekConfig

__all__ = [
    "LLMAdapter",
    "LLMResponse",
    "LLMError",
    "LLMConnectionError",
    "LLMAuthenticationError", 
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMConfigurationError",
    "DeepSeekAIAdapter",
    "DeepSeekConfig",
]