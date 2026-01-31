"""DefaultValueStrategy implementation for Seal library.

This module implements the DefaultValueStrategy that uses default values to
fill missing fields when validation fails due to missing required fields.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError

from ..base import DataCorrectionStrategy
from ..results import CorrectionResult


T = TypeVar('T', bound=SealModel)


class DefaultValueStrategy(DataCorrectionStrategy[T]):
    """Default value strategy that fills missing fields with default values.
    
    This strategy handles validation errors by identifying missing required
    fields and filling them with appropriate default values. It only applies
    to missing field errors and leaves other types of errors unchanged.
    
    This strategy produces corrected data that can be used directly.
    """
    
    def __init__(self, default_values: Optional[Dict[str, Any]] = None):
        """Initialize default value strategy.
        
        Args:
            default_values: Optional dictionary mapping field names to default values.
                          If not provided, the strategy will attempt to extract
                          default values from the model schema.
        """
        self.default_values = default_values or {}
    
    def correct(self, 
                data: Dict[str, Any], 
                errors: List[ValidationError],
                model: Type[T]) -> CorrectionResult:
        """Apply default value correction to fix validation errors.
        
        This method identifies missing field errors and attempts to fill them
        with default values. Other types of errors are not corrected.
        
        Args:
            data: The original data that failed validation
            errors: List of validation errors
            model: The target SealModel for validation
            
        Returns:
            CorrectionResult with corrected data if successful, or original data
            if no missing field errors were found or corrected.
        """
        corrected_data = data.copy()
        corrected_errors = []
        missing_field_errors = []
        
        # Separate missing field errors from other errors
        for error in errors:
            if self._is_missing_field_error(error):
                missing_field_errors.append(error)
            else:
                corrected_errors.append(error)
        
        # If no missing field errors, return original data with error summary
        if not missing_field_errors:
            error_summary = self._generate_error_summary(errors)
            return CorrectionResult(
                result=corrected_data,
                strategy_name=self.get_strategy_name(),
                error_summary=error_summary,
                correction_type=self.correction_type
            )
        
        # Attempt to fill missing fields with default values
        successful_corrections = []
        failed_corrections = []
        
        for error in missing_field_errors:
            field_name = error.field
            default_value = self._get_default_value(field_name, model)
            
            if default_value is not None:
                corrected_data[field_name] = default_value
                successful_corrections.append(f"{field_name} = {default_value}")
            else:
                failed_corrections.append(field_name)
                corrected_errors.append(error)  # Keep the error if no default value available
        
        # Generate error summary
        error_summary = self._generate_correction_summary(
            successful_corrections, 
            failed_corrections, 
            corrected_errors
        )
        
        return CorrectionResult(
            result=corrected_data,
            strategy_name=self.get_strategy_name(),
            error_summary=error_summary,
            correction_type=self.correction_type
        )
    
    def get_strategy_name(self) -> str:
        """Get the name of the correction strategy.
        
        Returns:
            String representing the strategy name
        """
        return "default_value"
    
    def _is_missing_field_error(self, error: ValidationError) -> bool:
        """Check if an error is a missing field error.
        
        Args:
            error: Validation error to check
            
        Returns:
            True if the error is a missing field error, False otherwise
        """
        error_type_lower = error.error_type.lower()
        error_message_lower = error.message.lower()
        
        return ("missing" in error_type_lower or 
                "missing" in error_message_lower or
                "required" in error_type_lower or
                "required" in error_message_lower)
    
    def _get_default_value(self, field_name: str, model: Type[T]) -> Optional[Any]:
        """Get default value for a field.
        
        Priority order:
        1. User-provided default values from constructor
        2. Default values from model schema
        3. Type-based default values
        
        Args:
            field_name: Name of the field to get default value for
            model: Target SealModel class
            
        Returns:
            Default value if available, None otherwise
        """
        # Check user-provided default values first
        if field_name in self.default_values:
            return self.default_values[field_name]
        
        # Try to get default value from model schema
        try:
            # Check if model has a schema method or attribute
            if hasattr(model, 'schema'):
                schema = model.schema()
                if isinstance(schema, dict) and 'properties' in schema:
                    field_props = schema['properties'].get(field_name, {})
                    if 'default' in field_props:
                        return field_props['default']
        except (AttributeError, KeyError):
            pass
        
        # Try to get type-based default value
        try:
            # Check if model has field annotations
            if hasattr(model, '__annotations__'):
                field_type = model.__annotations__.get(field_name)
                if field_type:
                    return self._get_type_default(field_type)
        except (AttributeError, KeyError):
            pass
        
        return None
    
    def _get_type_default(self, field_type: Any) -> Optional[Any]:
        """Get default value based on field type.
        
        Args:
            field_type: Type annotation for the field
            
        Returns:
            Default value for the type, or None if no suitable default
        """
        # Handle basic types
        type_str = str(field_type).lower()
        
        if 'int' in type_str or 'float' in type_str:
            return 0
        elif 'str' in type_str:
            return ""
        elif 'bool' in type_str:
            return False
        elif 'list' in type_str or 'tuple' in type_str:
            return []
        elif 'dict' in type_str:
            return {}
        
        # Handle Optional types (extract inner type)
        if hasattr(field_type, '__origin__') and field_type.__origin__ is Optional:
            inner_type = field_type.__args__[0]
            return self._get_type_default(inner_type)
        
        return None
    
    def _generate_error_summary(self, errors: List[ValidationError]) -> str:
        """Generate a summary of validation errors.
        
        Args:
            errors: List of validation errors
            
        Returns:
            String containing error summary
        """
        if not errors:
            return "No validation errors found."
        
        error_types = {}
        for error in errors:
            error_type = error.error_type
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        summary_parts = [f"Found {len(errors)} validation error(s):"]
        for error_type, count in error_types.items():
            summary_parts.append(f"- {count} {error_type} error(s)")
        
        return "\n".join(summary_parts)
    
    def _generate_correction_summary(self,
                                   successful_corrections: List[str],
                                   failed_corrections: List[str],
                                   remaining_errors: List[ValidationError]) -> str:
        """Generate a summary of correction results.
        
        Args:
            successful_corrections: List of successfully corrected fields
            failed_corrections: List of fields that couldn't be corrected
            remaining_errors: List of remaining validation errors
            
        Returns:
            String containing correction summary
        """
        summary_parts = []
        
        if successful_corrections:
            summary_parts.append("Successfully corrected fields:")
            for correction in successful_corrections:
                summary_parts.append(f"- {correction}")
            summary_parts.append("")
        
        if failed_corrections:
            summary_parts.append(f"Failed to correct {len(failed_corrections)} field(s) (no default value available):")
            for field in failed_corrections:
                summary_parts.append(f"- {field}")
            summary_parts.append("")
        
        if remaining_errors:
            error_types = {}
            for error in remaining_errors:
                error_type = error.error_type
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            summary_parts.append(f"{len(remaining_errors)} error(s) remain uncorrected:")
            for error_type, count in error_types.items():
                summary_parts.append(f"- {count} {error_type} error(s)")
        
        return "\n".join(summary_parts)