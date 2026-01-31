"""Integration tests for SealEngine with real LLM adapter."""

import pytest
import os
from typing import Dict, Any, List
from unittest.mock import Mock

from seal.codes.engine import SealEngine
from seal.codes.schema import SealModel
from seal.codes.llm.adapters.deepseek import DeepSeekAIAdapter, DeepSeekConfig
from seal.codes.parser import JsonParser
from seal.codes.prompt import PromptBuilder
from seal.codes.validation import Validator
from seal.codes.corrector import FixPromptStrategy
from seal.codes.engine.errors import MaxRetriesExceededError, EngineError


@pytest.fixture
def user_info_model():
    """Fixture for a user information model."""
    
    class UserInfo(SealModel):
        name: str
        age: int
        email: str
        
    return UserInfo


@pytest.fixture
def product_model():
    """Fixture for a product information model."""
    
    class Product(SealModel):
        name: str
        price: float
        category: str
        in_stock: bool
        
    return Product


@pytest.fixture
def deepseek_config():
    """Fixture for DeepSeek configuration."""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY environment variable not set")
        
    return DeepSeekConfig(
        api_key=api_key,
        model="deepseek-chat"
    )


@pytest.fixture
def deepseek_adapter(deepseek_config):
    """Fixture for DeepSeek AI adapter."""
    try:
        return DeepSeekAIAdapter(deepseek_config)
    except ImportError:
        pytest.skip("deepseek package not installed")


@pytest.fixture
def json_parser():
    """Fixture for JSON parser."""
    return JsonParser()


@pytest.fixture
def validator_factory():
    """Fixture for validator factory that creates validators for specific models."""
    def _create_validator(model):
        return Validator(model)
    return _create_validator


@pytest.fixture
def fix_prompt_strategy():
    """Fixture for fix prompt strategy."""
    return FixPromptStrategy(max_retries=3)


class TestSealEngineIntegration:
    """Integration test cases for SealEngine with real LLM adapter."""
    
    def test_seal_engine_integration_success(self, user_info_model, deepseek_adapter, json_parser, validator_factory, fix_prompt_strategy):
        """Test successful integration with real DeepSeek AI adapter."""
        
        validator = validator_factory(user_info_model)
        prompt_builder = PromptBuilder(user_info_model)
        
        engine = SealEngine[user_info_model](
            model=user_info_model,
            llm_adapter=deepseek_adapter,
            prompt_builder=prompt_builder,
            parser=json_parser,
            validator=validator,
            correctors=[fix_prompt_strategy]
        )
        
        prompt = """
        Please provide information about a fictional user named John Doe.
        He is 30 years old and his email is john.doe@example.com.
        """.strip()
        
        result = engine.run_sync(prompt)
        
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, user_info_model)
        assert result.data.name == "John Doe"
        assert result.data.age == 30
        assert result.data.email == "john.doe@example.com"
        assert result.retry_count == 0
        assert len(result.errors) == 0
        
        # Verify execution steps were recorded
        assert len(result.execution_log) > 0
        
        # Check that we have the expected steps
        step_types = [step.step_type for step in result.execution_log]
        assert 'llm_call' in step_types
        assert 'parse' in step_types
        assert 'validate' in step_types
        assert 'create_model' in step_types
    
    def test_seal_engine_integration_with_retry(self, product_model, deepseek_adapter, json_parser, validator_factory, fix_prompt_strategy):
        """Test integration with retry scenario."""
        
        validator = validator_factory(product_model)
        prompt_builder = PromptBuilder(product_model)
        
        engine = SealEngine[product_model](
            model=product_model,
            llm_adapter=deepseek_adapter,
            prompt_builder=prompt_builder,
            parser=json_parser,
            validator=validator,
            correctors=[fix_prompt_strategy]
        )
        
        # This prompt might cause the LLM to return incomplete data initially
        prompt = """
        Please provide information about a laptop product.
        The product should have a name, price, category, and stock status.
        """.strip()
        
        result = engine.run_sync(prompt)
        
        # The engine should handle any validation errors and retry if necessary
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, product_model)
        
        # Verify the data structure
        assert hasattr(result.data, 'name')
        assert hasattr(result.data, 'price')
        assert hasattr(result.data, 'category')
        assert hasattr(result.data, 'in_stock')
        
        # Price should be a positive number
        assert result.data.price > 0
        
        # Category should not be empty
        assert len(result.data.category) > 0
    
    def test_seal_engine_integration_complex_schema(self, deepseek_adapter, json_parser, validator_factory, fix_prompt_strategy):
        """Test integration with a more complex schema."""
        
        class Order(SealModel):
            order_id: str
            customer_name: str
            items: List[Dict[str, Any]]
            total_amount: float
            status: str
            
        validator = validator_factory(Order)
        prompt_builder = PromptBuilder(Order)
        
        engine = SealEngine[Order](
            model=Order,
            llm_adapter=deepseek_adapter,
            prompt_builder=prompt_builder,
            parser=json_parser,
            validator=validator,
            correctors=[fix_prompt_strategy]
        )
        
        prompt = """
        Please create a sample order with the following details:
        - Order ID: ORD-001
        - Customer: Alice Johnson
        - Items: 2 laptops at $999.99 each, 1 mouse at $29.99
        - Status: Processing
        """.strip()
        
        result = engine.run_sync(prompt)
        
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, Order)
        
        # Verify order details
        assert result.data.order_id == "ORD-001"
        assert result.data.customer_name == "Alice Johnson"
        assert result.data.status == "Processing"
        
        # Verify items structure
        assert isinstance(result.data.items, list)
        assert len(result.data.items) > 0
        
        # Verify total amount calculation
        assert result.data.total_amount > 0
    
    @pytest.mark.asyncio
    async def test_seal_engine_integration_async(self, user_info_model, deepseek_adapter, json_parser, validator_factory, fix_prompt_strategy):
        """Test asynchronous integration with real DeepSeek AI adapter."""
        
        validator = validator_factory(user_info_model)
        prompt_builder = PromptBuilder(user_info_model)
        
        engine = SealEngine[user_info_model](
            model=user_info_model,
            llm_adapter=deepseek_adapter,
            prompt_builder=prompt_builder,
            parser=json_parser,
            validator=validator,
            correctors=[fix_prompt_strategy]
        )
        
        prompt = """
        Please provide information about a fictional user named Sarah Smith.
        She is 25 years old and her email is sarah.smith@example.com.
        """.strip()
        
        result = await engine.run_async(prompt)
        
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, user_info_model)
        assert result.data.name == "Sarah Smith"
        assert result.data.age == 25
        assert result.data.email == "sarah.smith@example.com"
        assert result.retry_count == 0
        assert len(result.errors) == 0


class TestSealEngineErrorScenarios:
    """Test error scenarios in SealEngine integration."""
    
    @pytest.fixture
    def invalid_model(self):
        """Fixture for a model with strict validation requirements."""
        
        from pydantic import Field, EmailStr
        
        class StrictModel(SealModel):
            name: str
            age: int = Field(ge=0, le=150)  # Must be between 0 and 150
            email: EmailStr  # Must be valid email format
            
        return StrictModel
    
    def test_seal_engine_integration_max_retries(self, invalid_model, deepseek_adapter, json_parser, validator_factory, fix_prompt_strategy):
        """Test that max retries are respected when validation consistently fails."""
        
        validator = validator_factory(invalid_model)
        
        # Use a strategy with very low retries for this test
        low_retry_strategy = FixPromptStrategy(max_retries=0)  # No retries allowed
        prompt_builder = PromptBuilder(invalid_model)
        
        engine = SealEngine[invalid_model](
            model=invalid_model,
            llm_adapter=deepseek_adapter,
            prompt_builder=prompt_builder,
            parser=json_parser,
            validator=validator,
            correctors=[low_retry_strategy]
        )
        
        # This prompt explicitly asks for invalid data that should fail validation
        prompt = """
        Please provide user information with:
        - Name: "Test User"
        - Age: -5 (negative age, which is invalid)
        - Email: "invalid-email" (not a valid email format)
        """.strip()
        
        # The engine should raise EngineError after all correctors fail
        with pytest.raises(EngineError, match="All correctors failed to produce valid data"):
            engine.run_sync(prompt)
    
    def test_seal_engine_integration_with_custom_prompt(self, user_info_model, deepseek_adapter, json_parser, validator_factory, fix_prompt_strategy):
        """Test integration with custom prompt parameters."""
        
        validator = validator_factory(user_info_model)
        prompt_builder = PromptBuilder(user_info_model)
        
        engine = SealEngine[user_info_model](
            model=user_info_model,
            llm_adapter=deepseek_adapter,
            prompt_builder=prompt_builder,
            parser=json_parser,
            validator=validator,
            correctors=[fix_prompt_strategy]
        )
        
        prompt = """
        Create a user profile for a software developer.
        """.strip()
        
        # Test with custom temperature and max_tokens
        result = engine.run_sync(prompt, temperature=0.7, max_tokens=500)
        
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, user_info_model)
        
        # Verify basic user information structure
        assert len(result.data.name) > 0
        assert result.data.age > 0
        assert '@' in result.data.email  # Basic email validation