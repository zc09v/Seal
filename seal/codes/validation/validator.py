"""
Validator implementation for Seal library.

This module provides validation capabilities for structured data against Pydantic models,
with detailed error reporting and extensible custom validation rules.
"""

from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, ValidationError as PydanticValidationError

from seal.codes.schema import SealModel
from .errors import ValidationError, ValidationResult


T = TypeVar('T', bound=SealModel)


class ValidationRule:
    """
    Custom validation rule with metadata and execution logic.
    
    This class encapsulates a single validation rule that can be registered
    with a Validator to extend its validation capabilities beyond Pydantic's
    built-in validation.
    """
    
    def __init__(self, 
                 name: str,
                 validator_func: Callable[[Any, Dict[str, Any]], Union[bool, str]],
                 description: str = ""):
        """
        Initialize validation rule.
        
        Args:
            name: Unique name for the rule, used for identification and error reporting.
                 This name will appear in error messages (e.g., "CustomRule.{name}").
            validator_func: Validation function that takes two arguments:
                - value: The field value to validate (Any type)
                - context: Dictionary containing validation context with keys:
                    * 'field_name': Name of the field being validated
                    * 'data': Complete data dictionary being validated
                Returns:
                    - True: Validation passed
                    - False: Validation failed (generic error message)
                    - str: Validation failed with custom error message
            description: Optional description of the rule's purpose and behavior.
        """
        self.name = name
        self.validator_func = validator_func
        self.description = description
    
    def validate(self, value: Any, context: Dict[str, Any]) -> Optional[str]:
        """
        Execute validation rule.
        
        This method calls the registered validator function and processes its return value.
        The validator function receives the field value and context data, and can return:
        - True: Validation passed (returns None)
        - False: Validation failed (returns generic error message)
        - str: Validation failed with custom error message (returns the string)
        
        Args:
            value: The field value to validate
            context: Dictionary containing validation context with keys:
                - 'field_name': Name of the field being validated
                - 'data': Complete data dictionary being validated
            
        Returns:
            None if validation passed, error message string if validation failed
        """
        result = self.validator_func(value, context)
        
        if result is True:
            return None
        elif result is False:
            return f"Validation rule '{self.name}' failed"
        else:
            return str(result)


class Validator(Generic[T]):
    """
    Data validator that validates data against Pydantic models.
    
    This class provides comprehensive validation capabilities including:
    - Syntactic validation (type checking, format validation)
    - Semantic validation (field constraints, business rules)
    - Custom validation rules with extensible architecture
    - Detailed error reporting for correction strategies
    
    The validator combines Pydantic's built-in validation with custom validation
    rules that can be registered for specific fields. This allows extending
    validation beyond what Pydantic supports natively.
    """
    
    def __init__(self, model: Type[T]):
        """
        Initialize validator with a Pydantic model.
        
        Args:
            model: Pydantic model class defining data structure and constraints
        """
        self.model = model
        self._custom_rules: Dict[str, ValidationRule] = {}  # field_name -> single rule

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single data object against the model.
        
        Args:
            data: Dictionary containing data to validate
            
        Returns:
            ValidationResult containing validation status and error details
        """
        pydantic_errors = []
        
        try:
            # Use Pydantic's validation mechanism
            validated_instance = self.model(**data)
        except PydanticValidationError as e:
            # Extract Pydantic validation errors
            pydantic_errors = self._extract_validation_errors(e)
        
        # Execute custom validation rules
        custom_errors = self._execute_custom_validation(data)
        
        # Combine errors from both sources
        all_errors = pydantic_errors + custom_errors
        
        if len(all_errors) == 0:
            return ValidationResult(is_valid=True)
        else:
            return ValidationResult(is_valid=False, errors=all_errors)

    def register_rule(self, field_name: str, rule: ValidationRule) -> None:
        """
        Register a custom validation rule for a specific field.
        
        This method allows extending the validator with custom business logic
        that goes beyond Pydantic's built-in validation capabilities.
        
        Note: Each field can have only one custom validation rule. If you need
        multiple rules for a field, combine them into a single ValidationRule.
        
        Args:
            field_name: Name of the field to associate with this validation rule
            rule: ValidationRule instance containing the custom validation logic
            
        Raises:
            ValueError: If the field already has a validation rule registered
        """
        if field_name in self._custom_rules:
            raise ValueError(f"Field '{field_name}' already has a validation rule registered")
        
        self._custom_rules[field_name] = rule
    
    def remove_rule(self, field_name: str) -> bool:
        """
        Remove a validation rule for a specific field.
        
        Use this method to remove a previously registered custom validation rule.
        This is useful when you need to dynamically change validation behavior
        at runtime.
        
        Args:
            field_name: Name of the field to remove the validation rule from
            
        Returns:
            True if a rule was found and removed, False if no rule was registered
            for the specified field
        """
        if field_name in self._custom_rules:
            del self._custom_rules[field_name]
            return True
        return False
    
    def _execute_custom_validation(self, data: Dict[str, Any]) -> List[ValidationError]:
        """
        Execute custom validation rules.
        
        This method runs all registered custom validation rules against the
        provided data. It only validates fields that are present in the data
        and have registered validation rules.
        
        The validation process:
        1. Iterates through all registered custom rules
        2. For each rule, checks if the corresponding field exists in the data
        3. Executes the rule with the field value and context
        4. Collects any validation errors
        
        Args:
            data: Dictionary containing the data to validate
            
        Returns:
            List of ValidationError objects representing custom validation failures
        """
        errors = []
        
        # Execute field-specific rules
        for field_name, rule in self._custom_rules.items():
            if field_name in data:
                field_value = data[field_name]
                context = {'field_name': field_name, 'data': data}
                
                error_message = rule.validate(field_value, context)
                if error_message:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type=f"CustomRule.{rule.name}",
                        message=error_message,
                        value=field_value
                    ))
        
        return errors
    
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """
        Quick check if data is valid.
        
        Args:
            data: Dictionary containing data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            self.model(**data)
            
            # Also check custom rules
            custom_errors = self._execute_custom_validation(data)
            return len(custom_errors) == 0
            
        except PydanticValidationError:
            return False

    def _extract_validation_errors(self, validation_error: PydanticValidationError) -> List[ValidationError]:
        """
        Extract and format validation errors from Pydantic ValidationError.
        
        Args:
            validation_error: Pydantic ValidationError instance
            
        Returns:
            List of formatted ValidationError objects
        """
        errors = []
        
        for error in validation_error.errors():
            field_path = ' -> '.join(str(loc) for loc in error['loc'])
            error_type = error['type']  # Use Pydantic's original error type
            message = error['msg']
            
            # Extract the problematic value if available
            input_value = None
            if 'input' in error:
                input_value = error['input']
            
            errors.append(ValidationError(
                field=field_path,
                error_type=error_type,  # Directly use Pydantic error type
                message=message,
                value=input_value
            ))
        
        return errors