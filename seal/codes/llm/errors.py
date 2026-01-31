"""Error classes for LLM Adapter module."""


class LLMError(Exception):
    """Base exception for LLM adapter errors."""
    pass


class LLMConnectionError(LLMError):
    """Exception raised for connection-related errors."""
    pass


class LLMAuthenticationError(LLMError):
    """Exception raised for authentication failures."""
    pass


class LLMRateLimitError(LLMError):
    """Exception raised for rate limiting."""
    pass


class LLMTimeoutError(LLMError):
    """Exception raised for request timeouts."""
    pass


class LLMConfigurationError(LLMError):
    """Exception raised for configuration errors."""
    pass