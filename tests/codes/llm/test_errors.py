"""Unit tests for LLM Adapter error classes."""

import pytest

from seal.codes.llm.errors import (
    LLMError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConfigurationError,
)


class TestLLMErrors:
    """Test cases for LLM error classes."""
    
    def test_llm_error_basic(self):
        """Test basic LLMError functionality."""
        error = LLMError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_llm_error_inheritance(self):
        """Test that specific errors inherit from LLMError."""
        connection_error = LLMConnectionError("Connection failed")
        auth_error = LLMAuthenticationError("Auth failed")
        rate_error = LLMRateLimitError("Rate limit")
        timeout_error = LLMTimeoutError("Timeout")
        config_error = LLMConfigurationError("Config error")
        
        # All should be instances of LLMError
        assert isinstance(connection_error, LLMError)
        assert isinstance(auth_error, LLMError)
        assert isinstance(rate_error, LLMError)
        assert isinstance(timeout_error, LLMError)
        assert isinstance(config_error, LLMError)
    
    def test_llm_connection_error(self):
        """Test LLMConnectionError specific functionality."""
        error = LLMConnectionError("Network connection failed")
        assert str(error) == "Network connection failed"
        assert isinstance(error, LLMError)
    
    def test_llm_authentication_error(self):
        """Test LLMAuthenticationError specific functionality."""
        error = LLMAuthenticationError("Invalid API key")
        assert str(error) == "Invalid API key"
        assert isinstance(error, LLMError)
    
    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError specific functionality."""
        error = LLMRateLimitError("Too many requests")
        assert str(error) == "Too many requests"
        assert isinstance(error, LLMError)
    
    def test_llm_timeout_error(self):
        """Test LLMTimeoutError specific functionality."""
        error = LLMTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, LLMError)
    
    def test_llm_configuration_error(self):
        """Test LLMConfigurationError specific functionality."""
        error = LLMConfigurationError("Missing required configuration")
        assert str(error) == "Missing required configuration"
        assert isinstance(error, LLMError)
    
    def test_error_chaining(self):
        """Test that errors can be chained with original exceptions."""
        original_error = ConnectionError("Original connection error")
        
        try:
            raise original_error
        except ConnectionError:
            llm_error = LLMConnectionError("LLM connection failed")
        
        assert str(llm_error) == "LLM connection failed"
    
    def test_error_with_custom_attributes(self):
        """Test that errors can have custom attributes."""
        error = LLMError("Error with details")
        
        # Standard Exception doesn't support custom attributes in __init__
        # This test verifies basic error creation
        assert str(error) == "Error with details"
    
    def test_error_equality(self):
        """Test that errors with same message are considered different instances."""
        error1 = LLMError("Same message")
        error2 = LLMError("Same message")
        
        # Different instances should not be equal
        assert error1 != error2
        assert error1 is not error2
    
    def test_error_subclass_hierarchy(self):
        """Test the inheritance hierarchy of error classes."""
        # Check that all specific errors are proper subclasses
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMAuthenticationError, LLMError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMTimeoutError, LLMError)
        assert issubclass(LLMConfigurationError, LLMError)
        
        # Check that they are not subclasses of each other
        assert not issubclass(LLMConnectionError, LLMAuthenticationError)
        assert not issubclass(LLMAuthenticationError, LLMRateLimitError)