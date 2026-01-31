"""CorrectionResult class for Seal library.

This module defines the CorrectionResult class that encapsulates the outcome
of correction operations.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .types import CorrectionType


@dataclass
class CorrectionResult:
    """Result of correction operation.
    
    This class encapsulates the outcome of a correction operation.
    The type of result is determined by the strategy that produced it.
    """
    
    result: Optional[Any] = None
    """The result of the correction operation.
    
    The actual type of this result depends on the correction strategy:
    - Dict[str, Any] for corrected data
    - str for correction prompts
    - None for empty results
    """
    
    strategy_name: Optional[str] = None
    """Name of the correction strategy that produced this result."""
    
    error_summary: Optional[str] = None
    """Summary of validation errors that triggered the correction."""
    
    correction_type: Optional[CorrectionType] = None
    """Type of correction result, determined by the strategy."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the correction result
        """
        return {
            'correction_type': str(self.correction_type) if self.correction_type else None,
            'result': self.result,
            'strategy_name': self.strategy_name,
            'error_summary': self.error_summary
        }
    
    def __str__(self) -> str:
        """String representation of the correction result.
        
        Returns:
            Human-readable string representation
        """
        if self.correction_type == CorrectionType.CORRECTED_DATA:
            status = "SUCCESS"
        elif self.correction_type == CorrectionType.CORRECTION_PROMPT:
            status = "FAILED"
        else:
            status = "UNKNOWN"
            
        type_str = str(self.correction_type.value) if self.correction_type else "unknown"
        result_str = f"CorrectionResult({status}, type={type_str}, strategy={self.strategy_name})"
        
        if self.error_summary:
            result_str += f"\nErrors: {self.error_summary}"
        
        if self.correction_type == CorrectionType.CORRECTION_PROMPT and self.result:
            result_str += f"\nPrompt: {str(self.result)[:100]}..."
        
        return result_str