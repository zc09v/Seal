"""
Unit tests for validation error classes.
"""

import pytest
from seal.codes.validation.errors import ValidationError, ValidationResult


class TestValidationError:
    """Test ValidationError class."""
    
    def test_validation_error_creation(self):
        """Test creating a ValidationError."""
        error = ValidationError(
            field="name",
            error_type="TypeError",
            message="Expected string, got int",
            value=123
        )
        
        assert error.field == "name"
        assert error.error_type == "TypeError"
        assert error.message == "Expected string, got int"
        assert error.value == 123
    
    def test_validation_error_to_dict(self):
        """Test converting ValidationError to dictionary."""
        error = ValidationError(
            field="age",
            error_type="ValueError",
            message="Value must be positive",
            value=-5
        )
        
        error_dict = error.to_dict()
        
        assert error_dict == {
            'field': 'age',
            'error_type': 'ValueError',
            'message': 'Value must be positive',
            'value': -5
        }
    
    def test_validation_error_without_value(self):
        """Test ValidationError without value."""
        error = ValidationError(
            field="email",
            error_type="RequiredError",
            message="Field is required"
        )
        
        assert error.field == "email"
        assert error.error_type == "RequiredError"
        assert error.message == "Field is required"
        assert error.value is None


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_validation_result_valid(self):
        """Test valid ValidationResult."""
        result = ValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert result.errors == []
    
    def test_validation_result_invalid(self):
        """Test invalid ValidationResult with errors."""
        errors = [
            ValidationError("name", "TypeError", "Expected string", 123),
            ValidationError("age", "ValueError", "Must be positive", -5)
        ]
        
        result = ValidationResult(is_valid=False, errors=errors)
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.errors == errors
    
    def test_validation_result_get_error_messages(self):
        """Test getting error messages."""
        errors = [
            ValidationError("name", "TypeError", "Expected string", 123),
            ValidationError("age", "ValueError", "Must be positive", -5)
        ]
        
        result = ValidationResult(is_valid=False, errors=errors)
        messages = result.get_error_messages()
        
        assert messages == [
            "name: Expected string",
            "age: Must be positive"
        ]
    
    def test_validation_result_get_error_summary_valid(self):
        """Test error summary for valid result."""
        result = ValidationResult(is_valid=True)
        summary = result.get_error_summary()
        
        assert summary == "Validation passed"
    
    def test_validation_result_get_error_summary_invalid(self):
        """Test error summary for invalid result."""
        errors = [
            ValidationError("name", "TypeError", "Expected string", 123),
            ValidationError("age", "ValueError", "Must be positive", -5)
        ]
        
        result = ValidationResult(is_valid=False, errors=errors)
        summary = result.get_error_summary()
        
        expected_summary = "Validation failed with 2 error(s):\n  - name: Expected string\n  - age: Must be positive"
        assert summary == expected_summary
    
    def test_validation_result_empty_errors(self):
        """Test ValidationResult with empty errors list."""
        result = ValidationResult(is_valid=False, errors=[])
        
        assert result.is_valid is False
        assert result.errors == []
        assert result.get_error_messages() == []
        assert result.get_error_summary() == "Validation failed with 0 error(s):"