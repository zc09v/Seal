"""
Unit tests for Validator class.
"""

import pytest
from pydantic import BaseModel, Field
from typing import List, Optional

from seal.codes.validation import Validator, ValidationResult


class SimpleModel(BaseModel):
    """Simple test model."""
    name: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., ge=0, le=150)


class ComplexModel(BaseModel):
    """Complex test model with nested structures."""
    title: str = Field(..., min_length=1)
    count: int = Field(..., gt=0)
    tags: List[str] = Field(default_factory=list)
    optional_field: Optional[str] = None


class TestValidator:
    """Test Validator class."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = Validator(SimpleModel)
        assert validator.model == SimpleModel
    
    def test_validate_valid_data(self):
        """Test validating valid data."""
        validator = Validator(SimpleModel)
        valid_data = {"name": "John Doe", "age": 25}
        
        result = validator.validate(valid_data)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.errors == []
    
    def test_validate_invalid_type(self):
        """Test validating data with type errors."""
        validator = Validator(SimpleModel)
        invalid_data = {"name": "John Doe", "age": "twenty-five"}
        
        result = validator.validate(invalid_data)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.field == "age"
        assert "integer" in error.message.lower()
    
    def test_validate_invalid_constraint(self):
        """Test validating data with constraint violations."""
        validator = Validator(SimpleModel)
        invalid_data = {"name": "John Doe", "age": -5}
        
        result = validator.validate(invalid_data)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.field == "age"
        assert "greater than or equal to 0" in error.message
    
    def test_validate_missing_required_field(self):
        """Test validating data with missing required fields."""
        validator = Validator(SimpleModel)
        invalid_data = {"name": "John Doe"}  # age is missing
        
        result = validator.validate(invalid_data)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.field == "age"
        assert "required" in error.message.lower()
    
    def test_validate_complex_model(self):
        """Test validating data against complex model."""
        validator = Validator(ComplexModel)
        
        # Valid data
        valid_data = {
            "title": "Test Title",
            "count": 10,
            "tags": ["tag1", "tag2"]
        }
        
        result = validator.validate(valid_data)
        assert result.is_valid is True
        
        # Invalid data - multiple errors
        invalid_data = {
            "title": "",  # Too short
            "count": 0,   # Not greater than 0
            "tags": "not_a_list"  # Wrong type
        }
        
        result = validator.validate(invalid_data)
        assert result.is_valid is False
        assert len(result.errors) == 3
    
    def test_is_valid_method(self):
        """Test the is_valid quick check method."""
        validator = Validator(SimpleModel)
        
        # Valid data
        valid_data = {"name": "John Doe", "age": 25}
        assert validator.is_valid(valid_data) is True
        
        # Invalid data
        invalid_data = {"name": "John Doe", "age": "twenty-five"}
        assert validator.is_valid(invalid_data) is False
        
        # Missing field
        missing_field_data = {"name": "John Doe"}
        assert validator.is_valid(missing_field_data) is False
    
    def test_error_mapping(self):
        """Test that Pydantic error types are preserved."""
        validator = Validator(SimpleModel)
        
        # Type parsing error
        type_error_data = {"name": "John Doe", "age": "twenty-five"}
        result = validator.validate(type_error_data)
        error = result.errors[0]
        assert error.error_type == "int_parsing"  # Pydantic's original error type
        
        # Constraint error
        constraint_error_data = {"name": "John Doe", "age": -5}
        result = validator.validate(constraint_error_data)
        error = result.errors[0]
        assert error.error_type == "greater_than_equal"  # Pydantic's original error type
        
        # Required error
        required_error_data = {"name": "John Doe"}
        result = validator.validate(required_error_data)
        error = result.errors[0]
        assert error.error_type == "missing"  # Pydantic's original error type
    
    def test_error_extraction_with_nested_fields(self):
        """Test error extraction with nested field paths."""
        class NestedModel(BaseModel):
            user: SimpleModel
            
        validator = Validator(NestedModel)
        invalid_data = {
            "user": {
                "name": "John Doe",
                "age": "twenty-five"  # Type error in nested field
            }
        }
        
        result = validator.validate(invalid_data)
        assert result.is_valid is False
        assert len(result.errors) == 1
        
        error = result.errors[0]
        # Should show nested field path
        assert "user -> age" in error.field
    
    def test_empty_data_validation(self):
        """Test validating empty data."""
        validator = Validator(SimpleModel)
        empty_data = {}
        
        result = validator.validate(empty_data)
        assert result.is_valid is False
        # Should have errors for both required fields
        assert len(result.errors) == 2
    
    def test_extra_fields_ignored_by_default(self):
        """Test that extra fields are ignored by Pydantic's default behavior."""
        validator = Validator(SimpleModel)
        data_with_extra = {
            "name": "John Doe",
            "age": 25,
            "extra_field": "this should be ignored"
        }
        
        result = validator.validate(data_with_extra)
        # Extra fields should not cause validation errors
        assert result.is_valid is True


class TestCustomValidationRules:
    """Test custom validation rules functionality."""
    
    def test_register_and_validate_custom_rule(self):
        """Test registering and validating with custom rules."""
        from seal.codes.validation import ValidationRule
        
        validator = Validator(SimpleModel)
        
        # Create a custom rule
        def validate_name_no_numbers(value: str, context: dict) -> str:
            if any(char.isdigit() for char in value):
                return "Name should not contain numbers"
            return True
        
        name_rule = ValidationRule("no_numbers", validate_name_no_numbers)
        
        # Register the rule
        validator.register_rule("name", name_rule)
        
        # Test valid data
        valid_data = {"name": "Alice Smith", "age": 25}
        result = validator.validate(valid_data)
        assert result.is_valid is True
        
        # Test invalid data (name with numbers)
        invalid_data = {"name": "Alice123", "age": 25}
        result = validator.validate(invalid_data)
        assert result.is_valid is False
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.field == "name"
        assert error.error_type == "CustomRule.no_numbers"
        
        # Remove the rule
        assert validator.remove_rule("name") is True
        
        # Now the same data should be valid
        result = validator.validate(invalid_data)
        assert result.is_valid is True
    
    def test_rule_replacement(self):
        """Test that only one rule can be registered per field."""
        from seal.codes.validation import ValidationRule
        
        validator = Validator(SimpleModel)
        
        def validate_name_length(value: str, context: dict) -> str:
            if len(value) < 3:
                return "Name too short"
            return True
        
        def validate_name_format(value: str, context: dict) -> str:
            if not value[0].isupper():
                return "Name should start with uppercase"
            return True
        
        rule1 = ValidationRule("length", validate_name_length)
        rule2 = ValidationRule("format", validate_name_format)
        
        # Register first rule
        validator.register_rule("name", rule1)
        
        # Try to register second rule - should fail
        with pytest.raises(ValueError, match="already has a validation rule registered"):
            validator.register_rule("name", rule2)
        
        # Remove first rule
        validator.remove_rule("name")
        
        # Now register second rule
        validator.register_rule("name", rule2)
        
        # Test the new rule
        result = validator.validate({"name": "alice", "age": 25})
        assert result.is_valid is False
        assert result.errors[0].error_type == "CustomRule.format"
    
    def test_combined_pydantic_and_custom_validation(self):
        """Test combined Pydantic and custom validation."""
        from seal.codes.validation import ValidationRule
        
        validator = Validator(SimpleModel)
        
        # Register custom rule
        def validate_even_age(value: int, context: dict) -> str:
            if value % 2 != 0:
                return "Age should be even"
            return True
        
        age_rule = ValidationRule("even_age", validate_even_age)
        validator.register_rule("age", age_rule)
        
        # Test data with multiple errors
        invalid_data = {
            "name": "Bob123",  # Custom rule violation (numbers)
            "age": -5,        # Pydantic rule violation (negative) + custom rule (odd)
        }
        
        result = validator.validate(invalid_data)
        assert result.is_valid is False
        
        # Should have multiple errors
        error_types = {error.error_type for error in result.errors}
        assert "greater_than_equal" in error_types  # Pydantic error
        assert "CustomRule.even_age" in error_types  # Custom rule error
        
        # Name field should have custom rule error
        name_errors = [e for e in result.errors if e.field == "name"]
        assert len(name_errors) == 0  # No Pydantic error for name, but custom rule not registered for name
    
    def test_custom_rule_with_context(self):
        """Test custom rule that uses validation context."""
        from seal.codes.validation import ValidationRule
        
        validator = Validator(SimpleModel)
        
        def validate_name_in_context(value: str, context: dict) -> str:
            field_name = context.get('field_name', '')
            full_data = context.get('data', {})
            
            if field_name == "name" and "test" in value.lower():
                return f"Name should not contain 'test' in context of {field_name}"
            return True
        
        rule = ValidationRule("context_aware", validate_name_in_context)
        validator.register_rule("name", rule)
        
        # Test with context-aware validation
        result = validator.validate({"name": "Test User", "age": 25})
        assert result.is_valid is False
        assert "context" in result.errors[0].message.lower()


class TestBusinessRuleValidation:
    """Test business rule validation scenarios."""
    
    def test_business_rule_with_pydantic_validators(self):
        """Test business rules implemented using Pydantic validators."""
        from pydantic import validator, model_validator
        
        class OrderModel(BaseModel):
            start_date: str
            end_date: str
            quantity: int
            price: float
            
            @validator('end_date')
            def validate_dates(cls, end_date, values):
                if 'start_date' in values and end_date <= values['start_date']:
                    raise ValueError('end_date must be after start_date')
                return end_date
            
            @validator('quantity')
            def validate_quantity(cls, quantity):
                if quantity >= 1000:
                    raise ValueError('quantity must be less than 1000')
                return quantity
            
            @model_validator(mode='after')
            def validate_total_amount(self):
                total = self.quantity * self.price
                if total > 10000:
                    raise ValueError('total amount exceeds limit')
                return self
        
        validator = Validator(OrderModel)
        
        # Test valid data
        valid_data = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-10",
            "quantity": 10,
            "price": 100.0
        }
        result = validator.validate(valid_data)
        assert result.is_valid is True
        
        # Test business rule violation (date range)
        invalid_dates = {
            "start_date": "2024-01-10",
            "end_date": "2024-01-01",  # end_date before start_date
            "quantity": 10,
            "price": 100.0
        }
        result = validator.validate(invalid_dates)
        assert result.is_valid is False
        assert any("end_date must be after" in error.message for error in result.errors)
        
        # Test business rule violation (quantity)
        invalid_quantity = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-10",
            "quantity": 2000,  # Too large
            "price": 100.0
        }
        result = validator.validate(invalid_quantity)
        assert result.is_valid is False
        assert any("quantity must be less" in error.message for error in result.errors)
        
        # Test business rule violation (total amount)
        invalid_total = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-10",
            "quantity": 200,
            "price": 100.0  # Total = 20000 > 10000
        }
        result = validator.validate(invalid_total)
        assert result.is_valid is False
        assert any("total amount" in error.message for error in result.errors)