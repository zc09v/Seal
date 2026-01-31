"""SealModel base class for enhanced schema functionality."""

import json
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field


class SealModel(BaseModel):
    """
    Enhanced base model for Seal library.
    
    Provides additional functionality beyond standard Pydantic BaseModel,
    including example generation and future extensibility.
    """
    
    @classmethod
    def get_example(cls) -> Dict[str, Any]:
        """
        Generate example data based on field definitions.
        
        This method intelligently generates example data by:
        1. Using field-level 'example' attribute if provided
        2. Falling back to type-based default values
        3. Handling nested SealModel instances
        
        Returns:
            Dictionary containing example data.
        """
        example_data = {}
        
        for field_name, field_info in cls.model_fields.items():
            # Try to get example from field info
            example_value = cls._get_field_example(field_name, field_info)
            example_data[field_name] = example_value
        
        return example_data
    
    @classmethod
    def _get_field_example(cls, field_name: str, field_info: Any) -> Any:
        """
        Get example value for a specific field.
        
        Args:
            field_name: Name of the field
            field_info: Field information from model_fields
            
        Returns:
            Example value for the field
        """
        # Check if field has explicit example in json_schema_extra
        if hasattr(field_info, 'json_schema_extra') and field_info.json_schema_extra:
            if 'example' in field_info.json_schema_extra:
                return field_info.json_schema_extra['example']
        
        # Also check for deprecated extra parameter (backward compatibility)
        if hasattr(field_info, 'extra') and field_info.extra:
            if 'example' in field_info.extra:
                return field_info.extra['example']
        
        # Get the field annotation to determine type
        annotation = field_info.annotation
        
        # Handle basic types
        if annotation == str:
            return f"example_{field_name}"
        elif annotation == int:
            return 0
        elif annotation == float:
            return 0.0
        elif annotation == bool:
            return True
        elif annotation == list:
            return []
        elif annotation == dict:
            return {}
        
        # Handle Optional types
        if hasattr(annotation, '__origin__') and annotation.__origin__ == Optional:
            inner_type = annotation.__args__[0]
            return cls._get_field_example(field_name, type('Dummy', (), {'annotation': inner_type})())
        
        # Handle List types
        if hasattr(annotation, '__origin__') and annotation.__origin__ == list:
            item_type = annotation.__args__[0] if annotation.__args__ else Any
            # For lists, return a single item list if we can generate an example
            if item_type in (str, int, float, bool):
                example_item = cls._get_field_example(field_name, type('Dummy', (), {'annotation': item_type})())
                return [example_item]
            return []
        
        # Handle nested SealModel types
        try:
            if issubclass(annotation, SealModel):
                return annotation.get_example()
        except (TypeError, AttributeError):
            pass
        
        # Default fallback
        return None
    
    @classmethod
    def get_json_schema(cls) -> Dict[str, Any]:
        """
        Get JSON Schema representation of the model.
        
        Returns:
            JSON Schema dictionary
        """
        return cls.model_json_schema()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return self.model_dump()