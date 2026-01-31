"""Result classes for SealEngine execution."""

from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from seal.codes.schema import SealModel
from seal.codes.validation.errors import ValidationError


T = TypeVar('T', bound=SealModel)


@dataclass
class ExecutionStep:
    """Represents a single execution step in the engine process."""
    
    step_type: str
    """Type of step (e.g., 'llm_call', 'parse', 'validate', 'correct')"""
    
    input_data: Optional[Any] = None
    """Input data for this step"""
    
    output_data: Optional[Any] = None
    """Output data from this step"""
    
    success: bool = True
    """Whether this step was successful"""
    
    error: Optional[Exception] = None
    """Error if this step failed"""
    
    timestamp: Optional[float] = None
    """Timestamp when this step was executed"""


@dataclass
class EngineResult(Generic[T]):
    """Result of SealEngine execution."""
    
    success: bool
    """Whether the execution was successful"""
    
    data: Optional[T] = None
    """Validated data if successful"""
    
    errors: List[ValidationError] = field(default_factory=list)
    """Validation errors if failed"""
    
    retry_count: int = 0
    """Number of retry attempts"""
    
    execution_log: List[ExecutionStep] = field(default_factory=list)
    """Detailed execution log for debugging"""
    
    final_prompt: Optional[str] = None
    """The final prompt used in the last attempt"""
    
    def is_successful(self) -> bool:
        """Check if the execution was successful."""
        return self.success
    
    def get_data(self) -> Optional[T]:
        """Get the validated data if successful."""
        return self.data
    
    def get_errors(self) -> List[ValidationError]:
        """Get the validation errors if failed."""
        return self.errors
    
    def get_retry_count(self) -> int:
        """Get the number of retry attempts."""
        return self.retry_count
    
    def get_execution_log(self) -> List[ExecutionStep]:
        """Get the detailed execution log."""
        return self.execution_log
    
    def add_execution_step(self, step: ExecutionStep) -> None:
        """Add an execution step to the log."""
        self.execution_log.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary for serialization."""
        return {
            "success": self.success,
            "data": self.data.model_dump() if self.data else None,
            "errors": [
                {
                    "type": error.__class__.__name__,
                    "message": str(error),
                    "loc": getattr(error, "loc", None),
                    "input": getattr(error, "input", None)
                }
                for error in self.errors
            ],
            "retry_count": self.retry_count,
            "execution_steps": len(self.execution_log),
            "final_prompt": self.final_prompt
        }