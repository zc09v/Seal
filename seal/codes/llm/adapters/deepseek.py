"""DeepSeek AI adapter implementation."""

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

from ..base import LLMAdapter
from ..types import LLMResponse
from ..errors import (
    LLMError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConfigurationError,
)


@dataclass
class DeepSeekConfig:
    """Configuration for DeepSeek AI adapter."""
    
    api_key: str
    """API key for DeepSeek AI service."""
    
    base_url: str = "https://api.deepseek.com"
    """Base URL for the DeepSeek AI API."""
    
    model: str = "deepseek-chat"
    """Model name to use for completions."""


class DeepSeekAIAdapter(LLMAdapter):
    """Adapter for DeepSeek AI service.
    
    Note: This adapter requires the 'deepseek' package to be installed.
    Install it with: pip install deepseek
    """
    
    def __init__(self, config: DeepSeekConfig):
        """Initialize the DeepSeek AI adapter.
        
        Args:
            config: Configuration for the DeepSeek AI service.
            
        Raises:
            LLMConfigurationError: If the deepseek package is not installed.
        """
        self.config = config
        self._client = None
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are installed."""
        try:
            import deepseek  # noqa: F401
        except ImportError:
            raise LLMConfigurationError(
                "DeepSeek AI adapter requires the 'deepseek' package. "
                "Install it with: pip install deepseek"
            )
    
    def _get_client(self):
        """Get or create the DeepSeek client."""
        if self._client is None:
            from deepseek import DeepSeekAPI
            self._client = DeepSeekAPI(
                api_key=self.config.api_key
            )
        return self._client
    
    async def chat_completion(
        self,
        prompt: str,
        **kwargs: Any
    ) -> LLMResponse:
        """Perform an asynchronous chat completion using DeepSeek AI.
        
        Args:
            prompt: The input prompt string.
            **kwargs: Additional parameters for the LLM call.
            
        Returns:
            LLMResponse: The standardized response from DeepSeek AI.
            
        Raises:
            LLMError: If the API call fails.
        """
        # Since DeepSeekAPI only supports synchronous calls,
        # we run the synchronous method in a thread pool for async compatibility
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def sync_call():
            client = self._get_client()
            return client.chat_completion(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
        
        try:
            # Run synchronous call in thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                response_content = await loop.run_in_executor(executor, sync_call)
            
            # DeepSeekAPI returns the content directly as a string
            return LLMResponse(
                content=response_content,
                model=self.config.model,
                usage=None,  # DeepSeekAPI doesn't provide usage information
                finish_reason="stop",  # Assume completion
                raw_response=response_content
            )
            
        except Exception as e:
            # Map common exceptions to our error types
            error_message = str(e).lower()
            if "timeout" in error_message:
                raise LLMTimeoutError(f"Request timeout: {e}")
            elif "auth" in error_message or "401" in error_message or "403" in error_message:
                raise LLMAuthenticationError(f"Authentication failed: {e}")
            elif "rate limit" in error_message or "429" in error_message:
                raise LLMRateLimitError(f"Rate limit exceeded: {e}")
            elif "connection" in error_message or "network" in error_message:
                raise LLMConnectionError(f"Connection error: {e}")
            else:
                raise LLMError(f"DeepSeek AI API error: {e}")
    
    def chat_completion_sync(
        self,
        prompt: str,
        **kwargs: Any
    ) -> LLMResponse:
        """Perform a synchronous chat completion using DeepSeek AI.
        
        Args:
            prompt: The input prompt string.
            **kwargs: Additional parameters for the LLM call.
            
        Returns:
            LLMResponse: The standardized response from DeepSeek AI.
            
        Raises:
            LLMError: If the API call fails.
        """
        client = self._get_client()
        
        try:
            # Use the synchronous chat_completion method
            response_content = client.chat_completion(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            # DeepSeekAPI returns the content directly as a string
            return LLMResponse(
                content=response_content,
                model=self.config.model,
                usage=None,  # DeepSeekAPI doesn't provide usage information
                finish_reason="stop",  # Assume completion
                raw_response=response_content
            )
            
        except Exception as e:
            # Map common exceptions to our error types
            error_message = str(e).lower()
            if "timeout" in error_message:
                raise LLMTimeoutError(f"Request timeout: {e}")
            elif "auth" in error_message or "401" in error_message or "403" in error_message:
                raise LLMAuthenticationError(f"Authentication failed: {e}")
            elif "rate limit" in error_message or "429" in error_message:
                raise LLMRateLimitError(f"Rate limit exceeded: {e}")
            elif "connection" in error_message or "network" in error_message:
                raise LLMConnectionError(f"Connection error: {e}")
            else:
                raise LLMError(f"DeepSeek AI API error: {e}")