"""FixPromptStrategy implementation for Seal library.

This module implements the FixPromptStrategy that generates correction prompts
based on validation errors for LLM re-prompting.
"""

from typing import Any, Dict, Generic, List, Type, TypeVar

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError

from ..base import PromptCorrectionStrategy
from ..results import CorrectionResult


T = TypeVar('T', bound=SealModel)


class FixPromptStrategy(PromptCorrectionStrategy[T]):
    """Fix prompt strategy that generates correction prompts for LLM re-prompting.
    
    This strategy analyzes validation errors and generates detailed correction
    prompts that can be used to re-prompt the LLM with specific guidance on
    how to fix the identified issues.
    
    This strategy produces correction prompts and inherits retry configuration
    from the PromptCorrectionStrategy base class.
    """
    
    def __init__(self, max_retries: int = 3):
        """Initialize fix prompt strategy.
        
        Args:
            max_retries: Maximum number of retry attempts
        """
        super().__init__(max_retries)
    
    def correct(self, 
                data: Dict[str, Any], 
                errors: List[ValidationError],
                model: Type[T]) -> CorrectionResult:
        """Generate correction prompt based on validation errors.
        
        Args:
            data: The original data that failed validation
            errors: List of validation errors
            model: The target SealModel for validation
            
        Returns:
            CorrectionResult with correction prompt and error summary
        """
        error_summary = self._generate_error_summary(errors)
        correction_prompt = self._generate_correction_prompt(errors, model)
        
        return CorrectionResult(
            result=correction_prompt,
            strategy_name=self.get_strategy_name(),
            error_summary=error_summary,
            correction_type=self.correction_type
        )
    
    def get_strategy_name(self) -> str:
        """Get the name of the correction strategy.
        
        Returns:
            String representing the strategy name
        """
        return "fix_prompt"
    
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
    
    def _generate_correction_prompt(self, 
                                   errors: List[ValidationError],
                                   model: Type[T]) -> str:
        """Generate detailed correction prompt for LLM re-prompting.
        
        Args:
            errors: List of validation errors
            model: The target SealModel for validation
            
        Returns:
            String containing detailed correction instructions
        """
        if not errors:
            return "No validation errors to correct."
        
        prompt_parts = [
            "Validation failed. Please correct the following issues:",
            ""
        ]
        
        # Group errors by field for better organization
        field_errors = {}
        for error in errors:
            if error.field not in field_errors:
                field_errors[error.field] = []
            field_errors[error.field].append(error)
        
        # Generate correction instructions for each field
        for field_name, field_error_list in field_errors.items():
            prompt_parts.append(f"Field '{field_name}':")
            
            for error in field_error_list:
                correction_instruction = self._get_correction_instruction(error)
                prompt_parts.append(f"  - {error.message}")
                prompt_parts.append(f"    Correction: {correction_instruction}")
            
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Please provide the corrected data in the required JSON format.",
            "Ensure all field types, constraints, and business rules are satisfied."
        ])
        
        return "\n".join(prompt_parts)
    
    def _get_correction_instruction(self, error: ValidationError) -> str:
        """Get specific correction instruction for a validation error.
        
        Args:
            error: Validation error to generate instruction for
            
        Returns:
            String containing specific correction instruction
        """
        error_type = error.error_type.lower()
        
        # Map error types to specific correction instructions
        correction_instructions = {
            "type_error": "Ensure the value matches the expected data type",
            "value_error": "Provide a valid value that meets the constraints",
            "missing_field": "Include this required field in the response",
            "constraint_violation": "Ensure the value satisfies all constraints",
            "enum_error": "Choose a value from the allowed options",
            "custom_validation": "Follow the specific validation rules"
        }
        
        # Default instruction for unknown error types
        default_instruction = "Review and correct the value based on the error message"
        
        # Check for specific patterns in error messages
        error_message = error.message.lower()
        
        if "missing" in error_message or "required" in error_message:
            return "Include this required field with a valid value"
        elif "integer" in error_message and "string" in error_message:
            return "Convert the string value to an integer"
        elif "email" in error_message:
            return "Provide a valid email address format (e.g., user@example.com)"
        elif "greater than" in error_message or "less than" in error_message:
            return "Ensure the value satisfies the numerical constraints"
        
        # Return type-specific instruction or default
        return correction_instructions.get(error_type, default_instruction)