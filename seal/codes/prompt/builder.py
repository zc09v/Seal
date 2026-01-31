"""PromptBuilder implementation for Seal library."""

import json
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from seal.codes.schema import SealModel


T = TypeVar('T', bound=SealModel)


class PromptBuilder(Generic[T]):
    """Builder for converting SealModel to LLM format instructions."""
    
    def __init__(self, model: Type[T]):
        """
        Initialize PromptBuilder with a SealModel.
        
        Args:
            model: SealModel class to build format instructions for.
        """
        self.model = model
        self._json_schema: Optional[Dict[str, Any]] = None
    
    def to_json_schema(self) -> Dict[str, Any]:
        """
        Convert SealModel to JSON Schema.
        
        Returns:
            JSON Schema dictionary representing the model.
            
        Raises:
            ValueError: If the model cannot be converted to JSON Schema.
        """
        if self._json_schema is None:
            try:
                self._json_schema = self.model.model_json_schema()
            except Exception as e:
                raise ValueError(f"Failed to convert model to JSON Schema: {e}")
        return self._json_schema
    
    @property
    def format_instructions(self) -> str:
        """
        Generate format instructions for LLM.
        
        Returns:
            String containing format instructions in JSON Schema format.
        """
        schema = self.to_json_schema()
        
        # Format the JSON schema for readability
        formatted_schema = json.dumps(schema, indent=2, ensure_ascii=False)
        
        # Build the format instructions template
        instructions = f"""Please output data strictly according to the following JSON Schema format:

{formatted_schema}

"""
        
        # Add example section
        try:
            example = self.model.get_example()
            if example:
                formatted_example = json.dumps(example, indent=2, ensure_ascii=False)
                instructions += f"Example output format:\n{formatted_example}\n\n"
        except Exception:
            # Silently ignore errors in example generation
            pass
        
        # Add important notes
        instructions += """Important notes:
- Ensure all field types are correct
- Required fields must be provided
- Enum values must be within the specified range
- Numerical constraints must be satisfied
- Output must be valid JSON format
"""
        
        return instructions


def build_format_instructions(model: Type[SealModel]) -> str:
    """
    Convenience function to quickly generate format instructions.
    
    Args:
        model: SealModel class.
        
    Returns:
        Format instructions string.
    """
    builder = PromptBuilder[SealModel](model)
    return builder.format_instructions