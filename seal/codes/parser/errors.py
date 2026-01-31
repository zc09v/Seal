"""Error definitions for parser module."""

from typing import Optional


class JsonParseError(Exception):
    """JSON parsing error exception."""
    
    def __init__(self, message: str, original_text: str, error_details: Optional[str] = None):
        """
        Initialize parsing error.
        
        Args:
            message: Error message
            original_text: Original text content
            error_details: Detailed error information
        """
        self.message = message
        self.original_text = original_text
        self.error_details = error_details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Return formatted error message."""
        base_msg = f"JSON parsing error: {self.message}"
        if self.error_details:
            base_msg += f"\nDetails: {self.error_details}"
        base_msg += f"\nOriginal text: {self.original_text[:200]}{'...' if len(self.original_text) > 200 else ''}"
        return base_msg