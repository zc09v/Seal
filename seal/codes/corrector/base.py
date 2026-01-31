"""CorrectionStrategy abstract base classes for Seal library.

This module defines the abstract interfaces for correction strategies that
handle validation errors and provide correction mechanisms.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Type, TypeVar

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError
from .types import CorrectionType


T = TypeVar('T', bound=SealModel)


class CorrectionStrategy(Generic[T], ABC):
    """Abstract base class for all correction strategies.
    
    This class defines the common interface for correction strategies that handle
    validation errors and provide correction mechanisms.
    """
    
    @property
    @abstractmethod
    def correction_type(self) -> CorrectionType:
        """Get the type of correction result this strategy produces.
        
        Returns:
            CorrectionType enum value indicating the result type
        """
        pass
    
    @abstractmethod
    def correct(self, 
                data: Dict[str, Any], 
                errors: List[ValidationError],
                model: Type[T]) -> 'CorrectionResult':
        """Apply correction strategy to fix validation errors.
        
        Args:
            data: The original data that failed validation
            errors: List of validation errors
            model: The target SealModel for validation
            
        Returns:
            CorrectionResult containing the correction outcome
            
        Raises:
            NotImplementedError: If the method is not implemented by subclass
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of the correction strategy.
        
        Returns:
            String representing the strategy name
        """
        pass


class PromptCorrectionStrategy(CorrectionStrategy[T]):
    """Abstract base class for prompt-based correction strategies.
    
    This strategy produces correction prompts for re-prompting.
    It includes retry configuration for controlling the number of attempts.
    """
    
    def __init__(self, max_retries: int = 3):
        """Initialize prompt correction strategy.
        
        Args:
            max_retries: Maximum number of retry attempts
        """
        self.max_retries = max_retries
    
    @property
    def correction_type(self) -> CorrectionType:
        """Get the type of correction result this strategy produces.
        
        Returns:
            CorrectionType.CORRECTION_PROMPT for prompt-based strategies
        """
        return CorrectionType.CORRECTION_PROMPT


class DataCorrectionStrategy(CorrectionStrategy[T]):
    """Abstract base class for data correction strategies.
    
    This strategy produces corrected data that can be used directly.
    """
    
    @property
    def correction_type(self) -> CorrectionType:
        """Get the type of correction result this strategy produces.
        
        Returns:
            CorrectionType.CORRECTED_DATA for data correction strategies
        """
        return CorrectionType.CORRECTED_DATA