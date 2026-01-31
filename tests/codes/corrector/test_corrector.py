"""Unit tests for corrector module.

This module contains comprehensive tests for the correction strategies
and result classes in the corrector module.
"""

import unittest
from typing import Dict, Any
from unittest.mock import Mock

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError
from seal.codes.corrector import CorrectionStrategy, FixPromptStrategy, CorrectionResult
from seal.codes.corrector.types import CorrectionType


class TestSealModel(SealModel):
    """Test model for validation testing."""
    name: str
    age: int
    email: str


class TestCorrectionResult(unittest.TestCase):
    """Test cases for CorrectionResult class."""
    
    def test_correction_result_creation(self):
        """Test basic CorrectionResult creation."""
        # Test with corrected_data (successful correction)
        result_with_data = CorrectionResult(
            result={"name": "John", "age": 30},
            strategy_name="test_strategy",
            error_summary="No errors",
            correction_type=CorrectionType.CORRECTED_DATA
        )
        
        self.assertEqual(result_with_data.result, {"name": "John", "age": 30})
        self.assertEqual(result_with_data.strategy_name, "test_strategy")
        self.assertEqual(result_with_data.error_summary, "No errors")
        self.assertEqual(result_with_data.correction_type, CorrectionType.CORRECTED_DATA)
        
        # Test with correction_prompt (re-prompting needed)
        result_with_prompt = CorrectionResult(
            result="Test prompt",
            strategy_name="test_strategy",
            error_summary="Some errors",
            correction_type=CorrectionType.CORRECTION_PROMPT
        )
        
        self.assertEqual(result_with_prompt.result, "Test prompt")
        self.assertEqual(result_with_prompt.strategy_name, "test_strategy")
        self.assertEqual(result_with_prompt.error_summary, "Some errors")
        self.assertEqual(result_with_prompt.correction_type, CorrectionType.CORRECTION_PROMPT)
    
    def test_correction_result_to_dict(self):
        """Test Conversion to dictionary."""
        result = CorrectionResult(
            result="Prompt",
            strategy_name="test_strategy",
            error_summary="Errors found",
            correction_type=CorrectionType.CORRECTION_PROMPT
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict["correction_type"], "correction_prompt")
        self.assertEqual(result_dict["result"], "Prompt")
        self.assertEqual(result_dict["strategy_name"], "test_strategy")
        self.assertEqual(result_dict["error_summary"], "Errors found")
        
        # Test with corrected_data
        result_with_data = CorrectionResult(
            result={"test": "data"},
            strategy_name="test_strategy",
            correction_type=CorrectionType.CORRECTED_DATA
        )
        
        result_dict_with_data = result_with_data.to_dict()
        self.assertEqual(result_dict_with_data["correction_type"], "corrected_data")
        self.assertEqual(result_dict_with_data["result"], {"test": "data"})
    
    def test_correction_result_str_representation(self):
        """Test string representation."""
        # Test with corrected_data
        result_with_data = CorrectionResult(
            result={"test": "data"},
            correction_type=CorrectionType.CORRECTED_DATA
        )
        
        result_str = str(result_with_data)
        self.assertIn("SUCCESS", result_str)
        self.assertIn("type=corrected_data", result_str)
        self.assertIn("strategy=None", result_str)
        
        # Test with correction_prompt
        result_with_prompt = CorrectionResult(
            result="Test prompt",
            strategy_name="fix_prompt",
            correction_type=CorrectionType.CORRECTION_PROMPT
        )
        
        result_str_with_prompt = str(result_with_prompt)
        self.assertIn("FAILED", result_str_with_prompt)
        self.assertIn("type=correction_prompt", result_str_with_prompt)
        self.assertIn("strategy=fix_prompt", result_str_with_prompt)
        
        # Test with error summary
        result_with_errors = CorrectionResult(
            result="Prompt",
            error_summary="Test errors",
            correction_type=CorrectionType.CORRECTION_PROMPT
        )
        
        result_str_with_errors = str(result_with_errors)
        self.assertIn("FAILED", result_str_with_errors)
        self.assertIn("Test errors", result_str_with_errors)


class TestCorrectionStrategyInterface(unittest.TestCase):
    """Test cases for CorrectionStrategy abstract interface."""
    
    def test_abstract_methods(self):
        """Test that abstract methods are properly defined."""
        # Test that CorrectionStrategy is abstract
        with self.assertRaises(TypeError):
            CorrectionStrategy()  # Should raise TypeError for abstract class
        
        # Test that FixPromptStrategy implements all abstract methods
        strategy = FixPromptStrategy()
        self.assertTrue(hasattr(strategy, 'correct'))
        self.assertTrue(hasattr(strategy, 'get_strategy_name'))
        
        # Test that methods are callable
        self.assertTrue(callable(strategy.correct))
        self.assertTrue(callable(strategy.get_strategy_name))


if __name__ == '__main__':
    unittest.main()