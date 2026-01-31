"""Unit tests for DeepSeek AI adapter."""

import pytest
from unittest.mock import patch, Mock

from seal.codes.llm import DeepSeekAIAdapter, DeepSeekConfig
from seal.codes.llm.errors import LLMConfigurationError, LLMError


class TestDeepSeekConfig:
    """Test cases for DeepSeekConfig data class."""
    
    def test_basic_initialization(self):
        """Test basic DeepSeekConfig initialization."""
        config = DeepSeekConfig(api_key="test-key")
        
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.deepseek.com"
        assert config.model == "deepseek-chat"
    
    def test_custom_initialization(self):
        """Test DeepSeekConfig initialization with custom values."""
        config = DeepSeekConfig(
            api_key="custom-key",
            base_url="https://custom.api.com",
            model="custom-model"
        )
        
        assert config.api_key == "custom-key"
        assert config.base_url == "https://custom.api.com"
        assert config.model == "custom-model"


class TestDeepSeekAIAdapter:
    """Test cases for DeepSeekAIAdapter class."""
    
    def test_initialization_without_dependencies(self):
        """Test that adapter raises error when deepseek package is not installed."""
        config = DeepSeekConfig(api_key="test-key")
        
        # Mock import error
        with patch('builtins.__import__') as mock_import:
            mock_import.side_effect = ImportError("No module named 'deepseek'")
            
            with pytest.raises(LLMConfigurationError) as exc_info:
                DeepSeekAIAdapter(config)
            
            assert "deepseek" in str(exc_info.value)
            assert "pip install deepseek" in str(exc_info.value)
    
    def test_initialization_with_dependencies(self):
        """Test successful initialization when dependencies are available."""
        config = DeepSeekConfig(api_key="test-key")
        adapter = DeepSeekAIAdapter(config)
        
        assert adapter.config == config
        assert adapter._client is None
    
    def test_get_client_creation(self):
        """Test client creation in _get_client method."""
        config = DeepSeekConfig(api_key="test-key")
        adapter = DeepSeekAIAdapter(config)
        
        # Call _get_client
        client = adapter._get_client()
        
        # Verify client was created
        assert client is not None
        assert adapter._client == client
    
    def test_get_client_caching(self):
        """Test that client is cached after first creation."""
        config = DeepSeekConfig(api_key="test-key")
        adapter = DeepSeekAIAdapter(config)
        
        # First call
        client1 = adapter._get_client()
        
        # Second call should return cached client
        client2 = adapter._get_client()
        
        # Verify client was created only once
        assert client1 == client2
        assert adapter._client == client1
    
    def test_async_chat_completion_interface(self):
        """Test that async chat completion method exists and is callable."""
        config = DeepSeekConfig(api_key="test-key")
        adapter = DeepSeekAIAdapter(config)
        
        # Verify method exists
        assert hasattr(adapter, 'chat_completion')
        assert callable(adapter.chat_completion)
    
    def test_sync_chat_completion_interface(self):
        """Test that sync chat completion method exists and is callable."""
        config = DeepSeekConfig(api_key="test-key")
        adapter = DeepSeekAIAdapter(config)
        
        # Verify method exists
        assert hasattr(adapter, 'chat_completion_sync')
        assert callable(adapter.chat_completion_sync)
    
    def test_chat_completion_sync_success(self):
        """Test successful synchronous chat completion."""
        config = DeepSeekConfig(api_key="test-key")
        
        with patch('deepseek.DeepSeekAPI') as mock_api_class:
            mock_client = Mock()
            mock_client.chat_completion.return_value = "Test response"
            mock_api_class.return_value = mock_client
            
            adapter = DeepSeekAIAdapter(config)
            response = adapter.chat_completion_sync("Test prompt")
            
            assert response.content == "Test response"
            assert response.model == "deepseek-chat"
            assert response.finish_reason == "stop"
            
            # Verify API was called correctly
            mock_client.chat_completion.assert_called_once_with(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Test prompt"}]
            )
    
    def test_chat_completion_sync_error_handling(self):
        """Test error handling in synchronous chat completion."""
        config = DeepSeekConfig(api_key="test-key")
        
        with patch('deepseek.DeepSeekAPI') as mock_api_class:
            mock_client = Mock()
            mock_client.chat_completion.side_effect = Exception("Timeout error")
            mock_api_class.return_value = mock_client
            
            adapter = DeepSeekAIAdapter(config)
            
            with pytest.raises(Exception) as exc_info:
                adapter.chat_completion_sync("Test prompt")
            
            assert "Timeout error" in str(exc_info.value)
    
    def test_chat_completion_sync_timeout_error(self):
        """Test timeout error mapping in synchronous chat completion."""
        config = DeepSeekConfig(api_key="test-key")
        
        with patch('deepseek.DeepSeekAPI') as mock_api_class:
            mock_client = Mock()
            mock_client.chat_completion.side_effect = Exception("Request timeout")
            mock_api_class.return_value = mock_client
            
            adapter = DeepSeekAIAdapter(config)
            
            with pytest.raises(Exception) as exc_info:
                adapter.chat_completion_sync("Test prompt")
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_chat_completion_async_success(self):
        """Test successful asynchronous chat completion."""
        config = DeepSeekConfig(api_key="test-key")
        
        with patch('deepseek.DeepSeekAPI') as mock_api_class:
            mock_client = Mock()
            mock_client.chat_completion.return_value = "Test response"
            mock_api_class.return_value = mock_client
            
            adapter = DeepSeekAIAdapter(config)
            response = await adapter.chat_completion("Test prompt")
            
            assert response.content == "Test response"
            assert response.model == "deepseek-chat"
            assert response.finish_reason == "stop"
            
            # Verify API was called correctly
            mock_client.chat_completion.assert_called_once_with(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Test prompt"}]
            )
    
    @pytest.mark.asyncio
    async def test_chat_completion_async_error_handling(self):
        """Test error handling in asynchronous chat completion."""
        config = DeepSeekConfig(api_key="test-key")
        
        with patch('deepseek.DeepSeekAPI') as mock_api_class:
            mock_client = Mock()
            mock_client.chat_completion.side_effect = Exception("Network error")
            mock_api_class.return_value = mock_client
            
            adapter = DeepSeekAIAdapter(config)
            
            with pytest.raises(Exception) as exc_info:
                await adapter.chat_completion("Test prompt")
            
            assert "Network error" in str(exc_info.value)
    
    def test_error_mapping_authentication(self):
        """Test authentication error mapping."""
        config = DeepSeekConfig(api_key="test-key")
        
        with patch('deepseek.DeepSeekAPI') as mock_api_class:
            mock_client = Mock()
            mock_client.chat_completion.side_effect = Exception("401 Unauthorized")
            mock_api_class.return_value = mock_client
            
            adapter = DeepSeekAIAdapter(config)
            
            with pytest.raises(Exception) as exc_info:
                adapter.chat_completion_sync("Test prompt")
            
            assert "auth" in str(exc_info.value).lower()
    
    def test_error_mapping_rate_limit(self):
        """Test rate limit error mapping."""
        config = DeepSeekConfig(api_key="test-key")
        
        with patch('deepseek.DeepSeekAPI') as mock_api_class:
            mock_client = Mock()
            mock_client.chat_completion.side_effect = Exception("429 Rate limit")
            mock_api_class.return_value = mock_client
            
            adapter = DeepSeekAIAdapter(config)
            
            with pytest.raises(Exception) as exc_info:
                adapter.chat_completion_sync("Test prompt")
            
            assert "rate limit" in str(exc_info.value).lower()
    
    def test_error_mapping_connection(self):
        """Test connection error mapping."""
        config = DeepSeekConfig(api_key="test-key")
        
        with patch('deepseek.DeepSeekAPI') as mock_api_class:
            mock_client = Mock()
            mock_client.chat_completion.side_effect = Exception("Connection refused")
            mock_api_class.return_value = mock_client
            
            adapter = DeepSeekAIAdapter(config)
            
            with pytest.raises(Exception) as exc_info:
                adapter.chat_completion_sync("Test prompt")
            
            assert "connection" in str(exc_info.value).lower()


class TestDeepSeekAIAdapterIntegration:
    """Integration tests for DeepSeek AI adapter."""
    
    @pytest.mark.integration
    def test_real_api_call(self):
        """Test actual API call to DeepSeek AI (requires valid API key)."""
        # This test requires a valid API key and will be skipped if not available
        config = DeepSeekConfig(api_key="your deepseek api key")
        adapter = DeepSeekAIAdapter(config)
        
        # Simple test prompt
        prompt = "Hello, please respond with a short greeting."
        
        try:
            # Test synchronous call
            response = adapter.chat_completion_sync(prompt)
            
            # Verify response structure
            assert response is not None
            assert isinstance(response.content, str)
            assert len(response.content) > 0
            assert response.model == "deepseek-chat"
            assert response.raw_response is not None
            
        except LLMError as e:
            # If API call fails due to insufficient balance or other issues,
            # we skip the test instead of failing it
            if "insufficient balance" in str(e).lower():
                pytest.skip(f"Skipping test due to insufficient balance: {e}")
            elif "auth" in str(e).lower():
                pytest.skip(f"Skipping test due to authentication issues: {e}")
            else:
                # Re-raise other errors
                raise
    
    @pytest.mark.integration
    def test_async_api_call(self):
        """Test actual async API call to DeepSeek AI (requires valid API key)."""
        import asyncio
        
        config = DeepSeekConfig(api_key="your deepseek api key")
        adapter = DeepSeekAIAdapter(config)
        
        # Simple test prompt
        prompt = "Hello, please respond with a short greeting."
        
        try:
            # Test asynchronous call
            async def test_async():
                response = await adapter.chat_completion(prompt)
                return response
            
            response = asyncio.run(test_async())
            
            # Verify response structure
            assert response is not None
            assert isinstance(response.content, str)
            assert len(response.content) > 0
            assert response.model == "deepseek-chat"
            assert response.raw_response is not None
            
        except LLMError as e:
            # If API call fails due to insufficient balance or other issues,
            # we skip the test instead of failing it
            if "insufficient balance" in str(e).lower():
                pytest.skip(f"Skipping test due to insufficient balance: {e}")
            elif "auth" in str(e).lower():
                pytest.skip(f"Skipping test due to authentication issues: {e}")
            else:
                # Re-raise other errors
                raise