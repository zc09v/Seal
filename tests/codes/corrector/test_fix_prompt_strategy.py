"""Unit tests for FixPromptStrategy.

This module contains comprehensive tests for the FixPromptStrategy
that generates correction prompts based on validation errors.
"""

import unittest
from typing import Dict, Any
from unittest.mock import Mock

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError
from seal.codes.corrector import FixPromptStrategy, CorrectionResult
from seal.codes.corrector.types import CorrectionType


class TestSealModel(SealModel):
    """Test model for validation testing."""
    name: str
    age: int
    email: str


class TestFixPromptStrategy(unittest.TestCase):
    """Test cases for FixPromptStrategy class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.strategy = FixPromptStrategy()
        self.test_model = TestSealModel
        self.test_data = {"name": "John", "age": 30, "email": "john@example.com"}
    
    def test_strategy_name(self):
        """Test strategy name."""
        self.assertEqual(self.strategy.get_strategy_name(), "fix_prompt")
    
    def test_correction_with_empty_errors(self):
        """Test correction with no validation errors."""
        errors = []
        
        result = self.strategy.correct(self.test_data, errors, self.test_model)
        
        self.assertIsInstance(result, CorrectionResult)
        self.assertEqual(result.correction_type, CorrectionType.CORRECTION_PROMPT)
        self.assertEqual(result.strategy_name, "fix_prompt")
        self.assertIn("No validation errors found", result.error_summary)
    
    def test_correction_with_single_error(self):
        """Test correction with a single validation error."""
        errors = [
            ValidationError(
                field="age",
                error_type="type_error",
                message="Expected integer, got string",
                value="30"
            )
        ]
        
        result = self.strategy.correct(self.test_data, errors, self.test_model)
        
        self.assertIsInstance(result, CorrectionResult)
        self.assertEqual(result.correction_type, CorrectionType.CORRECTION_PROMPT)
        
        # Check error summary
        self.assertIn("Found 1 validation error(s)", result.error_summary)
        self.assertIn("1 type_error error(s)", result.error_summary)
        
        # Check correction prompt
        self.assertIn("Validation failed", str(result.result))
        self.assertIn("Field 'age'", str(result.result))
        self.assertIn("Expected integer, got string", str(result.result))
        self.assertIn("Convert the string value to an integer", str(result.result))
    
    def test_correction_with_multiple_errors(self):
        """Test correction with multiple validation errors."""
        errors = [
            ValidationError(
                field="age",
                error_type="type_error",
                message="Expected integer, got string",
                value="30"
            ),
            ValidationError(
                field="email",
                error_type="value_error",
                message="Invalid email format",
                value="invalid-email"
            ),
            ValidationError(
                field="name",
                error_type="missing_field",
                message="Field required",
                value=None
            )
        ]
        
        result = self.strategy.correct(self.test_data, errors, self.test_model)
        
        self.assertIsInstance(result, CorrectionResult)
        
        # Check error summary
        self.assertIn("Found 3 validation error(s)", result.error_summary)
        
        # Check correction prompt contains all fields
        prompt = str(result.result)
        self.assertIn("Field 'age'", prompt)
        self.assertIn("Field 'email'", prompt)
        self.assertIn("Field 'name'", prompt)
        
        # Check specific error messages
        self.assertIn("Expected integer, got string", prompt)
        self.assertIn("Invalid email format", prompt)
        self.assertIn("Field required", prompt)
    
    def test_error_summary_generation(self):
        """Test error summary generation with different error types."""
        errors = [
            ValidationError("field1", "type_error", "Error 1"),
            ValidationError("field2", "type_error", "Error 2"),
            ValidationError("field3", "value_error", "Error 3"),
            ValidationError("field4", "missing_field", "Error 4")
        ]
        
        summary = self.strategy._generate_error_summary(errors)
        
        self.assertIn("Found 4 validation error(s)", summary)
        self.assertIn("2 type_error error(s)", summary)
        self.assertIn("1 value_error error(s)", summary)
        self.assertIn("1 missing_field error(s)", summary)
    
    def test_correction_instruction_generation(self):
        """Test specific correction instruction generation."""
        # Test type error with integer/string conversion
        type_error = ValidationError("age", "type_error", "Expected integer, got string")
        instruction = self.strategy._get_correction_instruction(type_error)
        self.assertIn("Convert the string value to an integer", instruction)
        
        # Test missing field error
        missing_error = ValidationError("name", "missing_field", "Field required")
        instruction = self.strategy._get_correction_instruction(missing_error)
        self.assertIn("Include this required field", instruction)
        
        # Test email error
        email_error = ValidationError("email", "value_error", "Invalid email format")
        instruction = self.strategy._get_correction_instruction(email_error)
        self.assertIn("Provide a valid email address format", instruction)
        
        # Test numerical constraint error
        constraint_error = ValidationError("age", "value_error", "Value must be greater than 0")
        instruction = self.strategy._get_correction_instruction(constraint_error)
        self.assertIn("Ensure the value satisfies the numerical constraints", instruction)
        
        # Test unknown error type
        unknown_error = ValidationError("field", "unknown_error", "Some error")
        instruction = self.strategy._get_correction_instruction(unknown_error)
        self.assertIn("Review and correct the value", instruction)
        
        # Test generic type error (without specific pattern)
        generic_type_error = ValidationError("field", "type_error", "Type mismatch")
        instruction = self.strategy._get_correction_instruction(generic_type_error)
        self.assertIn("Ensure the value matches the expected data type", instruction)


if __name__ == '__main__':
    unittest.main()