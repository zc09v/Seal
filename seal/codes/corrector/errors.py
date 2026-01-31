"""Error types for corrector module.

This module defines error types specific to correction operations.
"""

from typing import Any, Optional


class CorrectionError(Exception):
    """Base exception for correction-related errors."""
    
    def __init__(self, message: str, strategy_name: Optional[str] = None):
        """Initialize correction error.
        
        Args:
            message: Error message
            strategy_name: Name of the strategy that caused the error
        """
        self.message = message
        self.strategy_name = strategy_name
        super().__init__(message)


class StrategyNotImplementedError(CorrectionError):
    """Exception raised when a correction strategy is not implemented."""
    
    def __init__(self, strategy_name: str):
        """Initialize strategy not implemented error.
        
        Args:
            strategy_name: Name of the strategy that is not implemented
        """
        message = f"Correction strategy '{strategy_name}' is not implemented"
        super().__init__(message, strategy_name)


class InvalidCorrectionDataError(CorrectionError):
    """Exception raised when correction data is invalid."""
    
    def __init__(self, message: str, data: Optional[Any] = None):
        """Initialize invalid correction data error.
        
        Args:
            message: Error message
            data: The invalid data that caused the error
        """
        self.data = data
        super().__init__(message)