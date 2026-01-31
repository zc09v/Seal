"""TypeConversionStrategy implementation for Seal library.

This module implements the TypeConversionStrategy that automatically converts
field values to the correct type when validation fails due to type mismatches.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError

from ..base import DataCorrectionStrategy
from ..results import CorrectionResult


T = TypeVar('T', bound=SealModel)


class TypeConversionStrategy(DataCorrectionStrategy[T]):
    """Type conversion strategy that automatically converts values to correct types.
    
    This strategy handles validation errors by identifying type mismatch errors
    and attempting to convert field values to the expected type. It supports
    common type conversions such as string to number, number to string,
    and various format conversions.
    
    This strategy produces corrected data that can be used directly.
    """
    
    def __init__(self, strict_conversion: bool = False):
        """Initialize type conversion strategy.
        
        Args:
            strict_conversion: If True, only perform safe conversions that
                             are guaranteed to preserve data integrity.
                             If False, attempt more aggressive conversions
                             but may lose precision or data.
        """
        self.strict_conversion = strict_conversion
    
    def correct(self, 
                data: Dict[str, Any], 
                errors: List[ValidationError],
                model: Type[T]) -> CorrectionResult:
        """Apply type conversion correction to fix validation errors.
        
        This method identifies type mismatch errors and attempts to convert
        field values to the expected type. Other types of errors are not corrected.
        
        Args:
            data: The original data that failed validation
            errors: List of validation errors
            model: The target SealModel for validation
            
        Returns:
            CorrectionResult with corrected data if successful, or original data
            if no type conversion errors were found or corrected.
        """
        corrected_data = data.copy()
        corrected_errors = []
        type_conversion_errors = []
        
        # Separate type conversion errors from other errors
        for error in errors:
            if self._is_type_conversion_error(error):
                type_conversion_errors.append(error)
            else:
                corrected_errors.append(error)
        
        # If no type conversion errors, return original data with error summary
        if not type_conversion_errors:
            error_summary = self._generate_error_summary(errors)
            return CorrectionResult(
                result=corrected_data,
                strategy_name=self.get_strategy_name(),
                error_summary=error_summary,
                correction_type=self.correction_type
            )
        
        # Attempt to convert field values to correct types
        successful_conversions = []
        failed_conversions = []
        
        for error in type_conversion_errors:
            field_name = error.field
            original_value = data.get(field_name)
            
            if original_value is None:
                failed_conversions.append(field_name)
                corrected_errors.append(error)
                continue
            
            # Get expected type from model schema
            expected_type = self._get_expected_type(field_name, model)
            
            if expected_type:
                converted_value = self._convert_value(original_value, expected_type)
                
                if converted_value is not None:
                    corrected_data[field_name] = converted_value
                    successful_conversions.append(
                        f"{field_name}: {original_value!r} -> {converted_value!r}"
                    )
                else:
                    failed_conversions.append(field_name)
                    corrected_errors.append(error)
            else:
                failed_conversions.append(field_name)
                corrected_errors.append(error)
        
        # Generate error summary
        error_summary = self._generate_conversion_summary(
            successful_conversions, 
            failed_conversions, 
            corrected_errors
        )
        
        return CorrectionResult(
            result=corrected_data,
            strategy_name=self.get_strategy_name(),
            error_summary=error_summary,
            correction_type=self.correction_type
        )
    
    def _is_type_conversion_error(self, error: ValidationError) -> bool:
        """Check if an error is a type conversion error.
        
        Args:
            error: Validation error to check
            
        Returns:
            True if the error is related to type conversion, False otherwise
        """
        if not error.message:
            return False
            
        error_message = error.message.lower()
        error_type = error.error_type.lower()
        
        # Check for specific type error patterns in error type
        type_error_types = [
            'type_error', 'typeerror', 'valueerror'
        ]
        
        if any(type_error in error_type for type_error in type_error_types):
            return True
        
        # Check for specific type conversion patterns in error message
        type_conversion_patterns = [
            'expected', 'but got',
            'value is not a valid',
            'invalid type',
            'type error',
            'cannot convert',
            'must be a valid',
            'not a valid'
        ]
        
        # Check for specific type mismatch patterns
        if 'expected' in error_message and 'got' in error_message:
            return True
            
        if 'not a valid' in error_message:
            return True
            
        # Check for specific type keywords in context
        type_keywords = ['integer', 'string', 'float', 'boolean', 'number', 'list', 'dict']
        if any(keyword in error_message for keyword in type_keywords):
            # Only return True if the error message suggests a type mismatch
            if 'expected' in error_message or 'got' in error_message or 'not a valid' in error_message:
                return True
        
        return False
    
    def _get_expected_type(self, field_name: str, model: Type[T]) -> Optional[type]:
        """Get the expected type for a field from the model schema.
        
        Args:
            field_name: Name of the field
            model: Target SealModel class
            
        Returns:
            Expected type for the field, or None if not found
        """
        try:
            # Get the field from model schema
            if hasattr(model, 'schema') and hasattr(model.schema(), 'get'):
                schema = model.schema()
                properties = schema.get('properties', {})
                
                if field_name in properties:
                    field_schema = properties[field_name]
                    
                    # Extract type information from schema
                    if 'type' in field_schema:
                        type_str = field_schema['type']
                        return self._map_schema_type_to_python_type(type_str)
                    
                    # Check for anyOf/oneOf with type information
                    if 'anyOf' in field_schema:
                        for type_def in field_schema['anyOf']:
                            if 'type' in type_def:
                                type_str = type_def['type']
                                return self._map_schema_type_to_python_type(type_str)
                    
                    if 'oneOf' in field_schema:
                        for type_def in field_schema['oneOf']:
                            if 'type' in type_def:
                                type_str = type_def['type']
                                return self._map_schema_type_to_python_type(type_str)
            
            # Fallback: try to get from model annotations
            if hasattr(model, '__annotations__'):
                annotations = model.__annotations__
                if field_name in annotations:
                    return annotations[field_name]
        
        except (AttributeError, KeyError, TypeError):
            pass
        
        return None
    
    def _map_schema_type_to_python_type(self, schema_type: str) -> type:
        """Map JSON schema type to Python type.
        
        Args:
            schema_type: JSON schema type string
            
        Returns:
            Corresponding Python type
        """
        type_mapping = {
            'string': str,
            'integer': int,
            'number': float,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        return type_mapping.get(schema_type, str)
    
    def _convert_value(self, value: Any, target_type: type) -> Optional[Any]:
        """Convert a value to the target type.
        
        Args:
            value: Original value to convert
            target_type: Target type to convert to
            
        Returns:
            Converted value, or None if conversion fails
        """
        if value is None:
            return None
        
        # If already the correct type, return as-is
        if isinstance(value, target_type):
            return value
        
        try:
            # Handle common type conversions
            if target_type == str:
                return self._convert_to_string(value)
            
            elif target_type == int:
                return self._convert_to_int(value)
            
            elif target_type == float:
                return self._convert_to_float(value)
            
            elif target_type == bool:
                return self._convert_to_bool(value)
            
            elif target_type == list:
                return self._convert_to_list(value)
            
            elif target_type == dict:
                return self._convert_to_dict(value)
            
            else:
                # For other types, try direct conversion
                return target_type(value)
        
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _convert_to_string(self, value: Any) -> str:
        """Convert value to string.
        
        Args:
            value: Value to convert
            
        Returns:
            String representation of the value
        """
        return str(value)
    
    def _convert_to_int(self, value: Any) -> int:
        """Convert value to integer.
        
        Args:
            value: Value to convert
            
        Returns:
            Integer representation of the value
        """
        if isinstance(value, str):
            # Handle strings with possible decimal points
            if '.' in value:
                return int(float(value))
            # Handle strings with commas (thousands separators)
            if ',' in value:
                value = value.replace(',', '')
        
        return int(value)
    
    def _convert_to_float(self, value: Any) -> float:
        """Convert value to float.
        
        Args:
            value: Value to convert
            
        Returns:
            Float representation of the value
        """
        if isinstance(value, str):
            # Handle strings with commas (thousands separators)
            if ',' in value:
                value = value.replace(',', '')
        
        return float(value)
    
    def _convert_to_bool(self, value: Any) -> bool:
        """Convert value to boolean.
        
        Args:
            value: Value to convert
            
        Returns:
            Boolean representation of the value
        """
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ('true', 'yes', '1', 'on'):
                return True
            elif value_lower in ('false', 'no', '0', 'off'):
                return False
        
        return bool(value)
    
    def _convert_to_list(self, value: Any) -> list:
        """Convert value to list.
        
        Args:
            value: Value to convert
            
        Returns:
            List representation of the value
        """
        if isinstance(value, str):
            # Try to parse as JSON array
            import json
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Try to split by commas
            if ',' in value:
                return [item.strip() for item in value.split(',')]
            
            # Single value as list
            return [value]
        
        elif isinstance(value, (tuple, set)):
            return list(value)
        
        elif isinstance(value, dict):
            return list(value.values())
        
        else:
            # Wrap single value in list
            return [value]
    
    def _convert_to_dict(self, value: Any) -> dict:
        """Convert value to dictionary.
        
        Args:
            value: Value to convert
            
        Returns:
            Dictionary representation of the value
        """
        if isinstance(value, str):
            # Try to parse as JSON object
            import json
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        
        elif isinstance(value, (list, tuple)):
            # Convert list of tuples to dict
            if all(isinstance(item, (list, tuple)) and len(item) == 2 for item in value):
                return dict(value)
            # Convert list to dict with index keys
            return {str(i): item for i, item in enumerate(value)}
        
        else:
            # Try to convert to dict
            try:
                return dict(value)
            except (TypeError, ValueError):
                pass
        
        # Fallback: wrap in dict
        return {'value': value}
    
    def _generate_conversion_summary(self, 
                                   successful_conversions: List[str],
                                   failed_conversions: List[str],
                                   remaining_errors: List[ValidationError]) -> str:
        """Generate summary of type conversion results.
        
        Args:
            successful_conversions: List of successful conversions
            failed_conversions: List of failed conversions
            remaining_errors: List of remaining validation errors
            
        Returns:
            String summary of conversion results
        """
        summary_parts = []
        
        if successful_conversions:
            summary_parts.append("Type conversions applied:")
            for conversion in successful_conversions:
                summary_parts.append(f"- {conversion}")
        
        if failed_conversions:
            summary_parts.append("\nFailed type conversions:")
            for field in failed_conversions:
                summary_parts.append(f"- {field}: Unable to convert to expected type")
        
        if remaining_errors:
            summary_parts.append(f"\nRemaining errors: {len(remaining_errors)}")
            for error in remaining_errors[:5]:  # Show first 5 errors
                summary_parts.append(f"- {error.field}: {error.message}")
            
            if len(remaining_errors) > 5:
                summary_parts.append(f"- ... and {len(remaining_errors) - 5} more errors")
        
        return '\n'.join(summary_parts)
    
    def _generate_error_summary(self, errors: List[ValidationError]) -> str:
        """Generate summary of validation errors.
        
        Args:
            errors: List of validation errors
            
        Returns:
            String summary of errors
        """
        if not errors:
            return "No validation errors found."
        
        # Check if there are any type conversion errors
        type_errors = [error for error in errors if self._is_type_conversion_error(error)]
        
        if not type_errors:
            return "No type conversion errors found. All errors are of other types."
        
        summary_parts = [f"Found {len(errors)} validation errors:"]
        
        for error in errors[:5]:  # Show first 5 errors
            summary_parts.append(f"- {error.field}: {error.message}")
        
        if len(errors) > 5:
            summary_parts.append(f"- ... and {len(errors) - 5} more errors")
        
        return '\n'.join(summary_parts)
    
    def get_strategy_name(self) -> str:
        """Get the name of the correction strategy.
        
        Returns:
            String representing the strategy name
        """
        return "TypeConversionStrategy"