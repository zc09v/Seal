"""Error definitions for SealEngine."""

from typing import Optional


class EngineError(Exception):
    """Base exception for engine-related errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class MaxRetriesExceededError(EngineError):
    """Exception raised when maximum retry attempts are exceeded."""
    
    def __init__(self, retry_count: int, max_retries: int, errors: list):
        message = f"Maximum retry attempts exceeded ({retry_count}/{max_retries})"
        details = f"Last validation errors: {errors}"
        super().__init__(message, details)
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.errors = errors


class LLMCallError(EngineError):
    """Exception raised when LLM API call fails."""
    
    def __init__(self, original_error: Exception, prompt: str):
        message = f"LLM API call failed: {original_error}"
        details = f"Prompt: {prompt[:200]}..." if len(prompt) > 200 else f"Prompt: {prompt}"
        super().__init__(message, details)
        self.original_error = original_error
        self.prompt = prompt