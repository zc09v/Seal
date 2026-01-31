"""Correction types for Seal library.

This module defines the CorrectionType enumeration that represents the different
types of correction results that a CorrectionStrategy can produce.
"""

from enum import Enum


class CorrectionType(Enum):
    """Enumeration of correction result types.
    
    This enum defines the possible types of correction results that a 
    CorrectionStrategy can produce. Each strategy should declare which type
    of result it produces.
    """
    
    CORRECTED_DATA = "corrected_data"
    """Strategy produces corrected data that can be used directly."""
    
    CORRECTION_PROMPT = "correction_prompt"
    """Strategy produces a correction prompt for re-prompting."""
    
    @classmethod
    def from_string(cls, value: str) -> 'CorrectionType':
        """Create CorrectionType from string value.
        
        Args:
            value: String representation of correction type
            
        Returns:
            Corresponding CorrectionType enum value
            
        Raises:
            ValueError: If the string value is not a valid correction type
        """
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid correction type: {value}. "
                           f"Valid types are: {[t.value for t in cls]}")
    
    def __str__(self) -> str:
        """String representation of the correction type."""
        return self.value