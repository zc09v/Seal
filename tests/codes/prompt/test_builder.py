"""Unit tests for PromptBuilder."""

import pytest
from typing import List, Optional
from pydantic import BaseModel, Field

from seal.codes.prompt import PromptBuilder, build_format_instructions
from seal.codes.schema import SealModel


class TestPromptBuilder:
    """Test cases for PromptBuilder class."""
    
    def test_prompt_builder_initialization(self):
        """Test that PromptBuilder can be initialized with a SealModel."""
        
        class SimpleModel(SealModel):
            name: str
            age: int
        
        builder = PromptBuilder(SimpleModel)
        assert builder.model == SimpleModel
    
    def test_to_json_schema_basic(self):
        """Test JSON Schema generation for a basic model."""
        
        class SimpleModel(SealModel):
            name: str
            age: int
        
        builder = PromptBuilder(SimpleModel)
        schema = builder.to_json_schema()
        
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert set(schema["required"]) == {"name", "age"}
    
    def test_to_json_schema_with_constraints(self):
        """Test JSON Schema generation with field constraints."""
        
        class ConstrainedModel(SealModel):
            name: str = Field(..., min_length=1, max_length=50)
            age: int = Field(..., ge=0, le=150)
            email: Optional[str] = Field(None)
        
        builder = PromptBuilder(ConstrainedModel)
        schema = builder.to_json_schema()
        
        name_props = schema["properties"]["name"]
        age_props = schema["properties"]["age"]
        email_props = schema["properties"]["email"]
        
        assert name_props["minLength"] == 1
        assert name_props["maxLength"] == 50
        assert age_props["minimum"] == 0
        assert age_props["maximum"] == 150
        assert "anyOf" in email_props  # Optional field
    
    def test_to_json_schema_caching(self):
        """Test that JSON Schema is cached after first generation."""
        
        class SimpleModel(SealModel):
            name: str
        
        builder = PromptBuilder(SimpleModel)
        
        # First call should generate schema
        schema1 = builder.to_json_schema()
        
        # Second call should return cached schema
        schema2 = builder.to_json_schema()
        
        assert schema1 is schema2  # Same object reference
    
    def test_sealmodel_example_integration(self):
        """Test that SealModel examples are integrated into format instructions."""
        
        class ExampleModel(SealModel):
            name: str = Field(..., json_schema_extra={'example': 'John Doe'})
            age: int = Field(..., json_schema_extra={'example': 25})
        
        builder = PromptBuilder(ExampleModel)
        instructions = builder.format_instructions
        
        # Should contain example section for SealModel
        assert "Example output format" in instructions
        assert "John Doe" in instructions
        assert "25" in instructions
    
    def test_format_instructions_structure(self):
        """Test that format instructions have correct structure."""
        
        class SimpleModel(SealModel):
            name: str
            age: int
        
        builder = PromptBuilder(SimpleModel)
        instructions = builder.format_instructions
        
        # Check that instructions contain key components
        assert "Please output data strictly according to the following JSON Schema format" in instructions
        assert "Important notes" in instructions
        assert "field types are correct" in instructions
        assert "Required fields must be provided" in instructions
        assert "valid JSON format" in instructions
    
    def test_format_instructions_contains_json_schema(self):
        """Test that format instructions contain the actual JSON Schema."""
        
        class SimpleModel(SealModel):
            name: str
        
        builder = PromptBuilder(SimpleModel)
        instructions = builder.format_instructions
        schema = builder.to_json_schema()
        
        # The JSON schema should be present in the instructions
        assert '"name"' in instructions
        assert '"type": "string"' in instructions
    
    def test_build_format_instructions_function(self):
        """Test the convenience function build_format_instructions."""
        
        class SimpleModel(SealModel):
            name: str
            age: int
        
        # Test convenience function
        instructions = build_format_instructions(SimpleModel)
        
        # Should produce the same result as using PromptBuilder directly
        builder = PromptBuilder(SimpleModel)
        expected_instructions = builder.format_instructions
        
        assert instructions == expected_instructions
    
    def test_complex_model_format_instructions(self):
        """Test format instructions generation for complex nested models."""
        
        class Address(SealModel):
            street: str
            city: str
            zip_code: str
        
        class UserProfile(SealModel):
            name: str = Field(..., min_length=1, max_length=50)
            age: int = Field(..., ge=0, le=150)
            email: Optional[str] = Field(None)
            addresses: List[Address] = Field(default_factory=list)
        
        builder = PromptBuilder(UserProfile)
        instructions = builder.format_instructions
        
        # Should contain all expected components
        assert "UserProfile" in instructions
        assert "Address" in instructions
        assert "name" in instructions
        assert "age" in instructions
        assert "email" in instructions
        assert "addresses" in instructions
    
    def test_error_handling_invalid_model(self):
        """Test error handling for invalid model input."""
        
        # Test with non-Pydantic class
        class NotAModel:
            name: str
        
        with pytest.raises(ValueError):
            builder = PromptBuilder(NotAModel)
            builder.to_json_schema()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_model(self):
        """Test PromptBuilder with an empty model."""
        
        class EmptyModel(SealModel):
            pass
        
        builder = PromptBuilder(EmptyModel)
        schema = builder.to_json_schema()
        instructions = builder.format_instructions
        
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert "required" not in schema or schema["required"] == []
        assert "Please output data strictly according to the following JSON Schema format" in instructions
    
    def test_model_with_only_optional_fields(self):
        """Test model where all fields are optional."""
        
        class OptionalModel(SealModel):
            name: Optional[str] = Field(None)
            age: Optional[int] = Field(None)
        
        builder = PromptBuilder(OptionalModel)
        schema = builder.to_json_schema()
        
        assert schema["type"] == "object"
        assert "required" not in schema or schema["required"] == []
    
    def test_model_with_list_and_dict_fields(self):
        """Test model with complex field types."""
        
        class ComplexModel(SealModel):
            tags: List[str]
            metadata: dict
            scores: List[float]
        
        builder = PromptBuilder(ComplexModel)
        schema = builder.to_json_schema()
        
        tags_props = schema["properties"]["tags"]
        metadata_props = schema["properties"]["metadata"]
        scores_props = schema["properties"]["scores"]
        
        assert tags_props["type"] == "array"
        assert metadata_props["type"] == "object"
        assert scores_props["type"] == "array"
        assert scores_props["items"]["type"] == "number"