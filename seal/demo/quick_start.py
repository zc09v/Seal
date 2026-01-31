"""
Quick Start Guide for Seal Library

A comprehensive example showing how to use Seal's core functionality for structured LLM output validation.
"""

from seal.codes.schema import SealModel, Field
from seal.codes.prompt import PromptBuilder, build_format_instructions
from seal.codes.validation import Validator, ValidationResult
from seal.codes.corrector import FixPromptStrategy, CorrectionResult, CorrectionType
from seal.codes.parser import JsonParser
from seal.codes.engine import SealEngine
from seal.codes.llm.adapters.deepseek import DeepSeekAIAdapter, DeepSeekConfig
from typing import List, Optional
import asyncio
import re


# Step 1: Define your data schema
class UserProfile(SealModel):
    """A simple user profile schema with validation constraints."""
    
    name: str = Field(..., min_length=1, max_length=50, 
                     json_schema_extra={'example': 'John Doe'})
    age: int = Field(..., ge=0, le=150, 
                    json_schema_extra={'example': 25})
    email: Optional[str] = Field(None, 
                               pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                               json_schema_extra={'example': 'john@example.com'})
    interests: List[str] = Field(default_factory=list)


def main():
    """Comprehensive Seal library demonstration."""
    
    print("Seal Quick Start - Structured LLM Output Validation")
    print("=" * 50)
    
    # Step 1: Basic data validation
    print("\n1. Basic Data Validation")
    print("-" * 30)
    
    user_data = {
        'name': 'Alice Johnson',
        'age': 28,
        'email': 'alice@example.com',
        'interests': ['reading', 'hiking']
    }
    
    user = UserProfile(**user_data)
    print(f"✅ Data validation passed: {user.name}, {user.age}")
    
    # Step 2: Generate example data
    print("\n2. Example Data Generation")
    print("-" * 30)
    
    example = UserProfile.get_example()
    print(f"✅ Example data generated:")
    for key, value in example.items():
        print(f"   {key}: {value}")
    
    # Step 3: Generate LLM format instructions
    print("\n3. LLM Format Instructions")
    print("-" * 30)
    
    instructions = build_format_instructions(UserProfile)
    print(f"✅ Format instructions generated ({len(instructions)} characters)")
    
    # Show a preview of the instructions
    print("\n--- Instructions Preview ---")
    lines = instructions.split('\n')
    for i, line in enumerate(lines[:8]):
        print(f"{line}")
    print("...")
    
    # Step 4: Advanced validation with Validator
    print("\n4. Advanced Validation")
    print("-" * 30)
    
    validator = Validator(UserProfile)
    
    # Test valid data
    valid_result = validator.validate(user_data)
    print(f"✅ Valid data validation: {valid_result.is_valid}")
    
    # Test invalid data
    invalid_data = {
        'name': '',  # Empty name (violates min_length constraint)
        'age': 200,  # Age too high (violates le constraint)
        'email': 'invalid-email',
        'interests': ['reading', 'hiking']
    }
    
    invalid_result = validator.validate(invalid_data)
    print(f"❌ Invalid data validation: {invalid_result.is_valid}")
    
    if not invalid_result.is_valid:
        print(f"   Errors found: {len(invalid_result.errors)}")
        for error in invalid_result.errors[:3]:  # Show first 3 errors
            print(f"   - {error}")
    
    # Step 5: Error handling demonstration
    print("\n5. Error Handling")
    print("-" * 30)

    # Apply correction strategy
    strategy = FixPromptStrategy()
    correction_result = strategy.correct(invalid_data, invalid_result.errors, UserProfile)
    
    print(f"✅ Correction strategy applied: {correction_result.strategy_name}")
    print(f"   Result type: {correction_result.correction_type}")
    
    if correction_result.correction_type == CorrectionType.CORRECTION_PROMPT and correction_result.result:
        print(f"\n--- Correction Prompt Preview ---")
        prompt_lines = str(correction_result.result).split('\n')[:6]
        for line in prompt_lines:
            print(f"   {line}")
        print("   ...")

    # Step 8: SealEngine demonstration with DeepSeekAIAdapter (Full automation)
    print("\n8. SealEngine - Full Automation with DeepSeek AI")
    print("-" * 30)
    
    # Setup components for SealEngine
    parser = JsonParser()
    validator = Validator(UserProfile)
    corrector = FixPromptStrategy(max_retries=1)
    
    print(f"✅ Engine components configured:")
    print(f"   - Parser: {type(parser).__name__}")
    print(f"   - Validator: {type(validator).__name__}")
    print(f"   - Corrector: {type(corrector).__name__}")
    
    # Demonstrate with real DeepSeek AI adapter (if API key is available)
    api_key = "your deepseek api key"  # From development guide
    
    if api_key:
        print(f"\n🔧 Setting up DeepSeek AI adapter...")
        
        try:
            # Configure DeepSeek AI adapter
            deepseek_config = DeepSeekConfig(
                api_key=api_key,
                model="deepseek-chat"
            )
            
            llm_adapter = DeepSeekAIAdapter(deepseek_config)
            
            # Create SealEngine with real adapter
            prompt_builder = PromptBuilder(UserProfile)
            
            engine = SealEngine[UserProfile](
                model=UserProfile,
                llm_adapter=llm_adapter,
                prompt_builder=prompt_builder,
                parser=parser,
                validator=validator,
                correctors=[corrector]  # 现在支持多个corrector
            )
 
            prompt = """
            Please create a user profile for a software developer named Alex Chen.
            Alex is -1 years old and interested in AI, programming, and hiking.
            """.strip()
            
            # also support async
            result = engine.run_sync(prompt)
            
            if result.success:
                user = result.data
                print(f"✅ Success! Generated user profile:")
                print(f"   Name: {user.name}")
                print(f"   Age: {user.age}")
                if user.email:
                    print(f"   Email: {user.email}")
                if user.interests:
                    print(f"   Interests: {', '.join(user.interests)}")
                print(f"   Retry attempts: {result.retry_count}")
                print(f"   Execution steps: {len(result.execution_log)}")
            else:
                print(f"❌ Failed after {result.retry_count} retry attempts")
                if result.errors:
                    print(f"   Errors: {len(result.errors)}")
                    for error in result.errors[:3]:
                        print(f"     - {error}")
            
            # Demonstrate error handling with invalid data
            print(f"\n🧪 Testing error handling with invalid data...")
            
            invalid_prompt = """
            Create a user profile with invalid data: negative age and empty name.
            """.strip()
            
            try:
                invalid_result = engine.run_sync(invalid_prompt)
                if invalid_result.success:
                    print(f"⚠️  Unexpected success with invalid data")
                else:
                    print(f"✅ Expected failure with invalid data")
                    print(f"   Retry attempts: {invalid_result.retry_count}")
            except Exception as e:
                print(f"✅ Exception caught: {type(e).__name__}")
            
        except ImportError:
            print(f"⚠️  DeepSeek package not installed. Install with: pip install deepseek")
        except Exception as e:
            print(f"⚠️  DeepSeek AI setup failed: {type(e).__name__}: {e}")
            print(f"   This is expected if the API key is invalid or network issues occur")
    else:
        print(f"⚠️  No DeepSeek API key found in environment")

    print("\n" + "=" * 50)
    print("🎉 You're ready to use Seal!")
    print("\nNext steps:")
    print("1. Use format instructions in your LLM prompts")
    print("2. Parse LLM responses using the schema")
    print("3. Validate data with Validator for detailed error reporting")
    print("4. Use FixPromptStrategy for automatic error correction")
    print("5. Implement retry logic based on correction results")
    print("6. Add custom validation rules for business logic")
    print("7. Use SealEngine for full automation with retry capabilities")

if __name__ == "__main__":
    main()