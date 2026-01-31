"""Abstract base class for LLM adapters."""

from abc import ABC, abstractmethod
from typing import Any

from .types import LLMResponse
from .errors import LLMError


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters.
    
    This class defines the minimal interface that all LLM adapters must implement.
    The design follows the principle of simplicity, providing only the core LLM 
    calling functionality without unnecessary metadata queries.
    """
    
    @abstractmethod
    async def chat_completion(
        self,
        prompt: str,
        **kwargs: Any
    ) -> LLMResponse:
        """Perform an asynchronous chat completion.
        
        Args:
            prompt: The input prompt string.
            **kwargs: Additional parameters for the LLM call.
            
        Returns:
            LLMResponse: The standardized response from the LLM.
            
        Raises:
            LLMError: If the LLM call fails for any reason.
        """
        pass
    
    @abstractmethod
    def chat_completion_sync(
        self,
        prompt: str,
        **kwargs: Any
    ) -> LLMResponse:
        """Perform a synchronous chat completion.
        
        Args:
            prompt: The input prompt string.
            **kwargs: Additional parameters for the LLM call.
            
        Returns:
            LLMResponse: The standardized response from the LLM.
            
        Raises:
            LLMError: If the LLM call fails for any reason.
        """
        pass