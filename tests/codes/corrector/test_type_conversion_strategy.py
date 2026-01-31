"""Unit tests for TypeConversionStrategy.

This module contains comprehensive tests for the TypeConversionStrategy
that automatically converts field values to the correct type.
"""

import unittest
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError
from seal.codes.corrector import TypeConversionStrategy, CorrectionResult
from seal.codes.corrector.types import CorrectionType


class TestSealModel(SealModel):
    """Test model for type conversion testing."""
    name: str
    age: int
    price: float
    active: bool
    tags: list
    metadata: dict
    
    @classmethod
    def schema(cls) -> Dict[str, Any]:
        """Mock schema for testing."""
        return {
            'properties': {
                'name': {'type': 'string'},
                'age': {'type': 'integer'},
                'price': {'type': 'number'},
                'active': {'type': 'boolean'},
                'tags': {'type': 'array'},
                'metadata': {'type': 'object'}
            }
        }


class TestTypeConversionStrategy(unittest.TestCase):
    """Test cases for TypeConversionStrategy class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.model = TestSealModel
        self.test_data = {
            'name': 'John',
            'age': 30,
            'price': 19.99,
            'active': True,
            'tags': ['tag1', 'tag2'],
            'metadata': {'key': 'value'}
        }
    
    def test_strategy_creation(self):
        """Test TypeConversionStrategy creation."""
        # Test with strict conversion
        strategy = TypeConversionStrategy(strict_conversion=True)
        self.assertTrue(strategy.strict_conversion)
        self.assertEqual(strategy.correction_type, CorrectionType.CORRECTED_DATA)
        self.assertEqual(strategy.get_strategy_name(), "TypeConversionStrategy")
        
        # Test with non-strict conversion
        strategy = TypeConversionStrategy(strict_conversion=False)
        self.assertFalse(strategy.strict_conversion)
    
    def test_is_type_conversion_error(self):
        """Test type conversion error detection."""
        strategy = TypeConversionStrategy()
        
        # Test type-related errors
        type_errors = [
            ValidationError(field='age', error_type='type_error', message='Expected integer, got string'),
            ValidationError(field='price', error_type='ValueError', message='value is not a valid float'),
            ValidationError(field='active', error_type='type', message='Expected boolean, got string'),
            ValidationError(field='tags', error_type='TypeError', message='Cannot convert to list'),
            ValidationError(field='metadata', error_type='error', message='Expected dict, but got list')
        ]
        
        for error in type_errors:
            self.assertTrue(strategy._is_type_conversion_error(error))
        
        # Test non-type errors
        non_type_errors = [
            ValidationError(field='name', error_type='missing_field', message='Field is required'),
            ValidationError(field='age', error_type='constraint', message='Value must be greater than 0'),
            ValidationError(field='email', error_type='format', message='Invalid email format')
        ]
        
        for error in non_type_errors:
            self.assertFalse(strategy._is_type_conversion_error(error))
    
    def test_convert_to_string(self):
        """Test string conversion."""
        strategy = TypeConversionStrategy()
        
        test_cases = [
            (123, "123"),
            (45.67, "45.67"),
            (True, "True"),
            ([1, 2, 3], "[1, 2, 3]"),
            ({'key': 'value'}, "{'key': 'value'}")
        ]
        
        for input_value, expected_output in test_cases:
            result = strategy._convert_to_string(input_value)
            self.assertEqual(result, expected_output)
    
    def test_convert_to_int(self):
        """Test integer conversion."""
        strategy = TypeConversionStrategy()
        
        test_cases = [
            ("123", 123),
            ("45.67", 45),
            ("1,000", 1000),
            (45.67, 45),
            (True, 1),
            (False, 0)
        ]
        
        for input_value, expected_output in test_cases:
            result = strategy._convert_to_int(input_value)
            self.assertEqual(result, expected_output)
    
    def test_convert_to_float(self):
        """Test float conversion."""
        strategy = TypeConversionStrategy()
        
        test_cases = [
            ("123.45", 123.45),
            ("1,000.50", 1000.5),
            (123, 123.0),
            ("45", 45.0)
        ]
        
        for input_value, expected_output in test_cases:
            result = strategy._convert_to_float(input_value)
            self.assertEqual(result, expected_output)
    
    def test_convert_to_bool(self):
        """Test boolean conversion."""
        strategy = TypeConversionStrategy()
        
        test_cases = [
            ("true", True),
            ("True", True),
            ("yes", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("no", False),
            ("0", False),
            (1, True),
            (0, False),
            ("random", True)  # Non-boolean strings are truthy
        ]
        
        for input_value, expected_output in test_cases:
            result = strategy._convert_to_bool(input_value)
            self.assertEqual(result, expected_output)
    
    def test_convert_to_list(self):
        """Test list conversion."""
        strategy = TypeConversionStrategy()
        
        test_cases = [
            ("[1, 2, 3]", [1, 2, 3]),  # JSON array
            ("item1,item2,item3", ["item1", "item2", "item3"]),  # CSV
            ("single", ["single"]),  # Single value
            ((1, 2, 3), [1, 2, 3]),  # Tuple
            ({1, 2, 3}, [1, 2, 3]),  # Set
            ({'a': 1, 'b': 2}, [1, 2])  # Dict values
        ]
        
        for input_value, expected_output in test_cases:
            result = strategy._convert_to_list(input_value)
            self.assertEqual(result, expected_output)
    
    def test_convert_to_dict(self):
        """Test dictionary conversion."""
        strategy = TypeConversionStrategy()
        
        test_cases = [
            ('{"key": "value"}', {'key': 'value'}),  # JSON object
            ([('a', 1), ('b', 2)], {'a': 1, 'b': 2}),  # List of tuples
            (['a', 'b', 'c'], {'0': 'a', '1': 'b', '2': 'c'})  # List with indices
        ]
        
        for input_value, expected_output in test_cases:
            result = strategy._convert_to_dict(input_value)
            self.assertEqual(result, expected_output)
    
    def test_correct_with_type_errors(self):
        """Test correction with type conversion errors."""
        strategy = TypeConversionStrategy()
        
        # Test data with type errors
        data = {
            'name': 'John',
            'age': '30',  # Should be converted to int
            'price': '19.99',  # Should be converted to float
            'active': 'true',  # Should be converted to bool
            'tags': 'tag1,tag2',  # Should be converted to list
            'metadata': '{"key": "value"}'  # Should be converted to dict
        }
        
        # Create type conversion errors
        errors = [
            ValidationError(field='age', error_type='type_error', message='Expected integer, got string'),
            ValidationError(field='price', error_type='ValueError', message='value is not a valid float'),
            ValidationError(field='active', error_type='type', message='Expected boolean, got string'),
            ValidationError(field='tags', error_type='TypeError', message='Cannot convert to list'),
            ValidationError(field='metadata', error_type='error', message='Expected dict, but got string')
        ]
        
        # Apply correction
        result = strategy.correct(data, errors, self.model)
        
        # Verify result
        self.assertEqual(result.correction_type, CorrectionType.CORRECTED_DATA)
        self.assertEqual(result.strategy_name, "TypeConversionStrategy")
        
        # Verify conversions
        self.assertEqual(result.result['age'], 30)
        self.assertEqual(result.result['price'], 19.99)
        self.assertEqual(result.result['active'], True)
        self.assertEqual(result.result['tags'], ['tag1', 'tag2'])
        self.assertEqual(result.result['metadata'], {'key': 'value'})
    
    def test_correct_with_mixed_errors(self):
        """Test correction with mixed type and non-type errors."""
        strategy = TypeConversionStrategy()
        
        # Test data with mixed errors
        data = {
            'name': 'John',
            'age': '30',  # Type error
            'price': 'invalid',  # Type error (cannot convert)
            'active': True
        }
        
        # Create mixed errors
        errors = [
            ValidationError(field='age', error_type='type_error', message='Expected integer, got string'),
            ValidationError(field='price', error_type='ValueError', message='value is not a valid float'),
            ValidationError(field='email', error_type='missing_field', message='Field is required')  # Non-type error
        ]
        
        # Apply correction
        result = strategy.correct(data, errors, self.model)
        
        # Verify result
        self.assertEqual(result.result['age'], 30)  # Should be converted
        self.assertEqual(result.result['price'], 'invalid')  # Should remain unchanged (conversion failed)
        self.assertIn('email', result.error_summary)  # Non-type error should be in summary
    
    def test_correct_with_no_type_errors(self):
        """Test correction when there are no type conversion errors."""
        strategy = TypeConversionStrategy()
        
        # Test data with no type errors
        data = {
            'name': 'John',
            'age': 30,
            'price': 19.99
        }
        
        # Create non-type errors
        errors = [
            ValidationError(field='email', error_type='missing_field', message='Field is required'),
            ValidationError(field='age', error_type='constraint', message='Value must be greater than 0')
        ]
        
        # Apply correction
        result = strategy.correct(data, errors, self.model)
        
        # Verify result (data should be unchanged)
        self.assertEqual(result.result, data)
        self.assertIn('email', result.error_summary)
        self.assertIn('age', result.error_summary)
    
    def test_get_expected_type_from_schema(self):
        """Test getting expected type from model schema."""
        strategy = TypeConversionStrategy()
        
        # Test getting types from schema
        self.assertEqual(strategy._get_expected_type('name', self.model), str)
        self.assertEqual(strategy._get_expected_type('age', self.model), int)
        self.assertEqual(strategy._get_expected_type('price', self.model), float)
        self.assertEqual(strategy._get_expected_type('active', self.model), bool)
        self.assertEqual(strategy._get_expected_type('tags', self.model), list)
        self.assertEqual(strategy._get_expected_type('metadata', self.model), dict)
        
        # Test non-existent field
        self.assertIsNone(strategy._get_expected_type('nonexistent', self.model))
    
    def test_map_schema_type_to_python_type(self):
        """Test mapping JSON schema types to Python types."""
        strategy = TypeConversionStrategy()
        
        type_mappings = [
            ('string', str),
            ('integer', int),
            ('number', float),
            ('boolean', bool),
            ('array', list),
            ('object', dict),
            ('unknown', str)  # Default fallback
        ]
        
        for schema_type, expected_python_type in type_mappings:
            result = strategy._map_schema_type_to_python_type(schema_type)
            self.assertEqual(result, expected_python_type)
    
    def test_convert_value_already_correct_type(self):
        """Test conversion when value is already correct type."""
        strategy = TypeConversionStrategy()
        
        test_cases = [
            ('hello', str, 'hello'),
            (42, int, 42),
            (3.14, float, 3.14),
            (True, bool, True),
            ([1, 2], list, [1, 2]),
            ({'key': 'value'}, dict, {'key': 'value'})
        ]
        
        for value, target_type, expected in test_cases:
            result = strategy._convert_value(value, target_type)
            self.assertEqual(result, expected)
    
    def test_convert_value_failure_cases(self):
        """Test conversion failure cases."""
        strategy = TypeConversionStrategy()
        
        # Test cases that should fail conversion
        failure_cases = [
            ('invalid', int),  # Cannot convert to int
            ('not_a_float', float),  # Cannot convert to float
            (None, int),  # None value
        ]
        
        for value, target_type in failure_cases:
            result = strategy._convert_value(value, target_type)
            self.assertIsNone(result)
        
        # Test cases that should return a default value when conversion fails
        default_cases = [
            ('invalid_json', dict, dict),  # Invalid JSON returns dict
            ('invalid_list', list, list),  # Invalid list format returns list
        ]
        
        for value, target_type, expected_type in default_cases:
            result = strategy._convert_value(value, target_type)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, expected_type)
    
    def test_convert_to_list_edge_cases(self):
        """Test edge cases for list conversion."""
        strategy = TypeConversionStrategy()
        
        # Test invalid JSON string
        result = strategy._convert_to_list('invalid json')
        self.assertEqual(result, ['invalid json'])
        
        # Test empty string
        result = strategy._convert_to_list('')
        self.assertEqual(result, [''])
        
        # Test None value
        result = strategy._convert_to_list(None)
        self.assertEqual(result, [None])
    
    def test_convert_to_dict_edge_cases(self):
        """Test edge cases for dictionary conversion."""
        strategy = TypeConversionStrategy()
        
        # Test invalid JSON string
        result = strategy._convert_to_dict('invalid json')
        # When JSON parsing fails, it should return a dict with the string as a value
        self.assertEqual(result, {'value': 'invalid json'})
        
        # Test empty string
        result = strategy._convert_to_dict('')
        self.assertEqual(result, {'value': ''})
        
        # Test None value
        result = strategy._convert_to_dict(None)
        self.assertEqual(result, {'value': None})
    
    def test_strict_conversion_mode(self):
        """Test behavior in strict conversion mode."""
        strategy_strict = TypeConversionStrategy(strict_conversion=True)
        strategy_non_strict = TypeConversionStrategy(strict_conversion=False)
        
        # Test data with potential precision loss
        data = {'age': '30.7'}
        errors = [ValidationError(field='age', error_type='type_error', message='Expected integer, got string')]
        
        # Apply correction with strict mode
        result_strict = strategy_strict.correct(data, errors, self.model)
        
        # Apply correction with non-strict mode
        result_non_strict = strategy_non_strict.correct(data, errors, self.model)
        
        # Both should convert to int (truncating decimal)
        self.assertEqual(result_strict.result['age'], 30)
        self.assertEqual(result_non_strict.result['age'], 30)
        
        # Check that both results are CorrectionResult instances
        self.assertEqual(result_strict.correction_type, CorrectionType.CORRECTED_DATA)
        self.assertEqual(result_strict.strategy_name, "TypeConversionStrategy")
        self.assertEqual(result_non_strict.correction_type, CorrectionType.CORRECTED_DATA)
        self.assertEqual(result_non_strict.strategy_name, "TypeConversionStrategy")

        # Check error summary
        self.assertIn("Type conversions applied:", result_strict.error_summary)
        self.assertIn("age: '30.7' -> 30", result_strict.error_summary)
    
    def test_correct_with_mixed_errors(self):
        """Test correction with mixed error types."""
        strategy = TypeConversionStrategy()
        
        # Test data with mixed errors
        data_with_errors = {
            'name': 'John',
            'age': '30',  # Type error
            'price': '19.99',  # Type error (string to float)
            'active': 'true'  # Type error
        }
        
        errors = [
            ValidationError(field='age', error_type='type_error', message='Expected integer, got string'),
            ValidationError(field='price', error_type='type_error', message='Expected float, got string'),
            ValidationError(field='active', error_type='type_error', message='Expected boolean, got string'),
            ValidationError(field='email', error_type='missing', message='Email is required')  # Missing field error
        ]
        
        result = strategy.correct(data_with_errors, errors, self.model)
        
        # Check result
        corrected_data = result.result
        
        # Only type errors should be corrected
        self.assertEqual(corrected_data['age'], 30)  # Converted to int
        self.assertEqual(corrected_data['price'], 19.99)  # Converted to float
        self.assertEqual(corrected_data['active'], True)  # Converted to bool
        
        # Other fields should remain unchanged
        self.assertEqual(corrected_data['name'], 'John')
        self.assertNotIn('email', corrected_data)  # Missing field not added
        
        # Check error summary
        self.assertIn("Type conversions applied:", result.error_summary)
        self.assertIn("Remaining errors: 1", result.error_summary)
    
    def test_correct_with_no_type_errors(self):
        """Test correction when no type errors are present."""
        strategy = TypeConversionStrategy()
        
        # Test data without type errors
        data_without_type_errors = {
            'name': 'John',
            'age': 30,
            'price': 19.99
        }
        
        errors = [
            ValidationError(field='email', error_type='missing', message='Email is required'),
            ValidationError(field='age', error_type='constraint', message='Age must be greater than 0')
        ]
        
        result = strategy.correct(data_without_type_errors, errors, self.model)
        
        # Data should remain unchanged
        self.assertEqual(result.result, data_without_type_errors)
        self.assertIn("No type conversion errors found", result.error_summary)
    
    def test_correct_with_conversion_failure(self):
        """Test correction when type conversion fails."""
        strategy = TypeConversionStrategy()
        
        # Test data with invalid conversions
        data_with_invalid = {
            'name': 'John',
            'age': 'not_a_number',  # Invalid int conversion
            'price': 'invalid_float',  # Invalid float conversion
            'active': 'yes'  # Valid bool conversion
        }
        
        errors = [
            ValidationError(field='age', error_type='type_error', message='Expected integer, got string'),
            ValidationError(field='price', error_type='type_error', message='Expected float, got string'),
            ValidationError(field='active', error_type='type_error', message='Expected boolean, got string')
        ]
        
        result = strategy.correct(data_with_invalid, errors, self.model)
        
        corrected_data = result.result
        
        # Only valid conversion should succeed
        self.assertEqual(corrected_data['active'], True)  # Valid conversion
        
        # Invalid conversions should remain as strings
        self.assertEqual(corrected_data['age'], 'not_a_number')
        self.assertEqual(corrected_data['price'], 'invalid_float')
        
        # Check error summary
        self.assertIn("Failed type conversions:", result.error_summary)
        self.assertIn("age: Unable to convert to expected type", result.error_summary)
    
    def test_get_expected_type(self):
        """Test getting expected type from model schema."""
        strategy = TypeConversionStrategy()
        
        # Test type extraction from schema
        expected_types = {
            'name': str,
            'age': int,
            'price': float,
            'active': bool,
            'tags': list,
            'metadata': dict
        }
        
        for field_name, expected_type in expected_types.items():
            result = strategy._get_expected_type(field_name, self.model)
            self.assertEqual(result, expected_type)
        
        # Test non-existent field
        result = strategy._get_expected_type('nonexistent', self.model)
        self.assertIsNone(result)
    
    def test_map_schema_type_to_python_type(self):
        """Test schema type to Python type mapping."""
        strategy = TypeConversionStrategy()
        
        test_cases = [
            ('string', str),
            ('integer', int),
            ('number', float),
            ('boolean', bool),
            ('array', list),
            ('object', dict),
            ('unknown', str)  # Default fallback
        ]
        
        for schema_type, expected_python_type in test_cases:
            result = strategy._map_schema_type_to_python_type(schema_type)
            self.assertEqual(result, expected_python_type)


if __name__ == '__main__':
    unittest.main()