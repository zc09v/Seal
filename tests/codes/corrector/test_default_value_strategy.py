"""Unit tests for DefaultValueStrategy.

This module contains comprehensive tests for the DefaultValueStrategy
that fills missing fields with default values.
"""

import unittest
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError
from seal.codes.corrector import DefaultValueStrategy, CorrectionResult
from seal.codes.corrector.types import CorrectionType


class TestSealModel(SealModel):
    """Test model for validation testing."""
    name: str
    age: int
    email: str
    optional_field: Optional[str] = None
    
    @classmethod
    def schema(cls) -> Dict[str, Any]:
        """Mock schema for testing."""
        return {
            'properties': {
                'name': {'type': 'string', 'default': 'Unknown'},
                'age': {'type': 'integer', 'default': 0},
                'email': {'type': 'string'},
                'optional_field': {'type': 'string', 'default': 'default_optional'}
            }
        }


class TestDefaultValueStrategy(unittest.TestCase):
    """Test cases for DefaultValueStrategy class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.model = TestSealModel
        self.test_data = {'name': 'John', 'age': 30}
    
    def test_strategy_creation(self):
        """Test DefaultValueStrategy creation."""
        # Test with default values
        strategy = DefaultValueStrategy(default_values={'missing_field': 'default_value'})
        self.assertEqual(strategy.default_values, {'missing_field': 'default_value'})
        self.assertEqual(strategy.correction_type, CorrectionType.CORRECTED_DATA)
        self.assertEqual(strategy.get_strategy_name(), 'default_value')
        
        # Test without default values
        strategy_empty = DefaultValueStrategy()
        self.assertEqual(strategy_empty.default_values, {})
    
    def test_correct_with_missing_fields(self):
        """Test correction with missing field errors."""
        # Create missing field errors
        errors = [
            ValidationError(field='email', error_type='missing_field', 
                           message='Field email is required'),
            ValidationError(field='optional_field', error_type='missing_field', 
                           message='Field optional_field is required')
        ]
        
        strategy = DefaultValueStrategy()
        result = strategy.correct(self.test_data, errors, self.model)
        
        # Check result type and content
        self.assertIsInstance(result, CorrectionResult)
        self.assertEqual(result.correction_type, CorrectionType.CORRECTED_DATA)
        self.assertEqual(result.strategy_name, 'default_value')
        
        # Check corrected data
        corrected_data = result.result
        self.assertIsInstance(corrected_data, dict)
        self.assertEqual(corrected_data['name'], 'John')
        self.assertEqual(corrected_data['age'], 30)
        self.assertEqual(corrected_data['email'], '')  # Type-based default for string
        self.assertEqual(corrected_data['optional_field'], 'default_optional')  # Schema default
        
        # Check error summary
        self.assertIn('Successfully corrected fields:', result.error_summary)
        self.assertIn('email = ', result.error_summary)
        self.assertIn('optional_field = default_optional', result.error_summary)
    
    def test_correct_with_user_provided_defaults(self):
        """Test correction with user-provided default values."""
        errors = [
            ValidationError(field='email', error_type='missing_field', 
                           message='Field email is required'),
            ValidationError(field='optional_field', error_type='missing_field', 
                           message='Field optional_field is required')
        ]
        
        user_defaults = {'email': 'user@example.com', 'optional_field': 'user_default'}
        strategy = DefaultValueStrategy(default_values=user_defaults)
        result = strategy.correct(self.test_data, errors, self.model)
        
        corrected_data = result.result
        self.assertEqual(corrected_data['email'], 'user@example.com')  # User default
        self.assertEqual(corrected_data['optional_field'], 'user_default')  # User default
    
    def test_correct_with_non_missing_errors(self):
        """Test correction with non-missing field errors."""
        # Create non-missing field errors
        errors = [
            ValidationError(field='age', error_type='type_error', 
                           message='Field age must be integer', value='thirty'),
            ValidationError(field='email', error_type='format_error', 
                           message='Invalid email format', value='invalid_email')
        ]
        
        strategy = DefaultValueStrategy()
        result = strategy.correct(self.test_data, errors, self.model)
        
        # Should return original data since no missing field errors
        corrected_data = result.result
        self.assertEqual(corrected_data, self.test_data)
        self.assertIn('type_error', result.error_summary)
        self.assertIn('format_error', result.error_summary)
    
    def test_correct_with_mixed_errors(self):
        """Test correction with mixed error types."""
        errors = [
            ValidationError(field='email', error_type='missing_field', 
                           message='Field email is required'),
            ValidationError(field='age', error_type='type_error', 
                           message='Field age must be integer', value='thirty')
        ]
        
        strategy = DefaultValueStrategy()
        result = strategy.correct(self.test_data, errors, self.model)
        
        corrected_data = result.result
        # Email should be corrected
        self.assertEqual(corrected_data['email'], '')
        # Age should remain unchanged (type error not corrected)
        self.assertEqual(corrected_data['age'], 30)
        
        # Check error summary includes both correction and remaining errors
        self.assertIn('Successfully corrected fields:', result.error_summary)
        self.assertIn('email = ', result.error_summary)
        self.assertIn('type_error error(s)', result.error_summary)
    
    def test_correct_with_no_errors(self):
        """Test correction with no validation errors."""
        strategy = DefaultValueStrategy()
        result = strategy.correct(self.test_data, [], self.model)
        
        corrected_data = result.result
        self.assertEqual(corrected_data, self.test_data)
        self.assertIn('No validation errors found.', result.error_summary)
    
    def test_is_missing_field_error(self):
        """Test missing field error detection."""
        strategy = DefaultValueStrategy()
        
        # Test missing field errors
        missing_errors = [
            ValidationError(field='test', error_type='missing_field', message='Field is missing'),
            ValidationError(field='test', error_type='MISSING', message='Field is missing'),
            ValidationError(field='test', error_type='required', message='Field is required'),
            ValidationError(field='test', error_type='REQUIRED', message='Field is required'),
            ValidationError(field='test', error_type='other', message='Field is missing'),
            ValidationError(field='test', error_type='other', message='Field is required'),
        ]
        
        for error in missing_errors:
            self.assertTrue(strategy._is_missing_field_error(error))
        
        # Test non-missing field errors
        non_missing_errors = [
            ValidationError(field='test', error_type='type_error', message='Wrong type'),
            ValidationError(field='test', error_type='format_error', message='Invalid format'),
            ValidationError(field='test', error_type='constraint', message='Constraint violation'),
        ]
        
        for error in non_missing_errors:
            self.assertFalse(strategy._is_missing_field_error(error))
    
    def test_get_default_value_priority(self):
        """Test default value priority order."""
        strategy = DefaultValueStrategy(default_values={'name': 'user_default'})
        
        # User-provided default should have highest priority
        value = strategy._get_default_value('name', self.model)
        self.assertEqual(value, 'user_default')
        
        # Schema default should be used if no user default
        value = strategy._get_default_value('optional_field', self.model)
        self.assertEqual(value, 'default_optional')
        
        # Type-based default should be used if no schema default
        value = strategy._get_default_value('email', self.model)
        self.assertEqual(value, '')  # String default
    
    def test_get_type_default(self):
        """Test type-based default value generation."""
        strategy = DefaultValueStrategy()
        
        # Test basic types
        self.assertEqual(strategy._get_type_default(int), 0)
        self.assertEqual(strategy._get_type_default(float), 0)
        self.assertEqual(strategy._get_type_default(str), '')
        self.assertEqual(strategy._get_type_default(bool), False)
        self.assertEqual(strategy._get_type_default(list), [])
        self.assertEqual(strategy._get_type_default(dict), {})
        
        # Test type strings
        self.assertEqual(strategy._get_type_default('int'), 0)
        self.assertEqual(strategy._get_type_default('str'), '')
        
        # Test unknown types
        self.assertIsNone(strategy._get_type_default(object))
    
    def test_correct_with_failed_corrections(self):
        """Test correction when some fields cannot be corrected."""
        # Create error for field that has no default value
        errors = [
            ValidationError(field='unknown_field', error_type='missing_field', 
                           message='Field unknown_field is required')
        ]
        
        strategy = DefaultValueStrategy()
        result = strategy.correct(self.test_data, errors, self.model)
        
        corrected_data = result.result
        # Unknown field should not be added (no default value available)
        self.assertNotIn('unknown_field', corrected_data)
        
        # Check error summary includes failed correction
        self.assertIn('Failed to correct 1 field(s)', result.error_summary)
        self.assertIn('unknown_field', result.error_summary)
    
    def test_correct_preserves_original_data(self):
        """Test that correction preserves original data fields."""
        errors = [
            ValidationError(field='email', error_type='missing_field', 
                           message='Field email is required')
        ]
        
        original_data = {'name': 'John', 'age': 30, 'custom_field': 'custom_value'}
        strategy = DefaultValueStrategy()
        result = strategy.correct(original_data, errors, self.model)
        
        corrected_data = result.result
        # Original fields should be preserved
        self.assertEqual(corrected_data['name'], 'John')
        self.assertEqual(corrected_data['age'], 30)
        self.assertEqual(corrected_data['custom_field'], 'custom_value')
        # Missing field should be added
        self.assertEqual(corrected_data['email'], '')


if __name__ == '__main__':
    unittest.main()