"""
Validation error types and result classes for Seal library.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """
    Encapsulates validation error information.
    """
    field: str
    error_type: str
    message: str
    value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format for serialization.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            'field': self.field,
            'error_type': self.error_type,
            'message': self.message,
            'value': self.value
        }


class ValidationResult:
    """
    Encapsulates validation results.
    """
    
    def __init__(self, is_valid: bool, errors: Optional[List[ValidationError]] = None):
        """
        Initialize validation result.
        
        Args:
            is_valid: Whether validation passed
            errors: List of validation errors
        """
        self._is_valid = is_valid
        self._errors = errors or []

    @property
    def is_valid(self) -> bool:
        """Whether validation passed."""
        return self._is_valid

    @property
    def errors(self) -> List[ValidationError]:
        """List of validation errors."""
        return self._errors

    def get_error_messages(self) -> List[str]:
        """
        Get formatted error messages.
        
        Returns:
            List of formatted error messages
        """
        return [f"{error.field}: {error.message}" for error in self._errors]

    def get_error_summary(self) -> str:
        """
        Get error summary.
        
        Returns:
            Formatted error summary string
        """
        if self.is_valid:
            return "Validation passed"
        
        error_count = len(self._errors)
        if error_count == 0:
            return "Validation failed with 0 error(s):"
        
        messages = self.get_error_messages()
        return f"Validation failed with {error_count} error(s):\n" + "\n".join(f"  - {msg}" for msg in messages)