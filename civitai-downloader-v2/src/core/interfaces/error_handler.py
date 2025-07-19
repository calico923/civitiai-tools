"""
ErrorHandler - Abstract interface for error handling implementations.

This module defines the abstract base class for implementing error handling
strategies including retry logic, fallback mechanisms, and error classification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union, Type
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import asyncio


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Error category classification."""
    NETWORK = "network"
    AUTHENTICATION = "authentication" 
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    RESOURCE = "resource"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class RetryStrategy(Enum):
    """Retry strategy types."""
    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED_INTERVAL = "fixed_interval"
    CUSTOM = "custom"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    component: str
    operation: str
    retry_count: int
    max_retries: int
    fallback_available: bool
    original_error: Exception
    timestamp: datetime
    context_data: Optional[Dict[str, Any]] = None


@dataclass
class RetryConfig:
    """Retry configuration parameters."""
    strategy: RetryStrategy
    max_retries: int
    base_delay: float
    max_delay: float
    backoff_multiplier: float = 2.0
    jitter: bool = True
    timeout: Optional[float] = None


@dataclass
class FallbackOption:
    """Fallback option configuration."""
    name: str
    handler: Callable[..., Any]
    priority: int
    condition: Optional[Callable[[Exception], bool]] = None
    timeout: Optional[float] = None


@dataclass
class ErrorHandlingResult:
    """Result of error handling operation."""
    success: bool
    retry_attempted: bool
    fallback_used: Optional[str]
    final_error: Optional[Exception]
    execution_time: float
    context: ErrorContext


class ErrorHandler(ABC):
    """
    Abstract base class for error handling implementations.
    
    This interface defines the contract for implementing error handling
    strategies including classification, retry logic, and fallback mechanisms.
    """
    
    @abstractmethod
    def handle_error(self, 
                    error: Exception, 
                    context: ErrorContext) -> ErrorHandlingResult:
        """
        Handle an error with appropriate strategy.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            ErrorHandlingResult with handling outcome
            
        Raises:
            ErrorHandlingError: If error handling itself fails
        """
        pass
    
    @abstractmethod
    def should_retry(self, 
                    error: Exception, 
                    context: ErrorContext) -> bool:
        """
        Determine if operation should be retried based on error and context.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            True if retry should be attempted
        """
        pass
    
    @abstractmethod
    def get_fallback(self, 
                    error: Exception, 
                    context: ErrorContext) -> Optional[FallbackOption]:
        """
        Get appropriate fallback option for the error.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            FallbackOption if available, None otherwise
        """
        pass
    
    @abstractmethod
    def classify_error(self, error: Exception) -> ErrorCategory:
        """
        Classify error into appropriate category.
        
        Args:
            error: The exception to classify
            
        Returns:
            ErrorCategory for the error
        """
        pass
    
    @abstractmethod
    def get_error_severity(self, error: Exception) -> ErrorSeverity:
        """
        Determine severity level of the error.
        
        Args:
            error: The exception to assess
            
        Returns:
            ErrorSeverity level for the error
        """
        pass
    
    @abstractmethod
    def calculate_retry_delay(self, 
                            attempt: int, 
                            config: RetryConfig) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            attempt: Current retry attempt number (1-based)
            config: Retry configuration
            
        Returns:
            Delay in seconds before next retry
        """
        pass
    
    @abstractmethod
    async def execute_with_retry(self, 
                               operation: Callable[..., Any],
                               config: RetryConfig,
                               context: ErrorContext,
                               *args, **kwargs) -> Any:
        """
        Execute operation with retry logic.
        
        Args:
            operation: Function to execute
            config: Retry configuration
            context: Error context for tracking
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of successful operation
            
        Raises:
            Exception: If all retries are exhausted
        """
        pass
    
    @abstractmethod
    def register_fallback(self, 
                         error_type: Type[Exception],
                         fallback: FallbackOption) -> None:
        """
        Register fallback handler for specific error type.
        
        Args:
            error_type: Exception type to handle
            fallback: Fallback option configuration
            
        Raises:
            ValidationError: If fallback configuration is invalid
        """
        pass
    
    @abstractmethod
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error handling statistics.
        
        Returns:
            Dictionary with error statistics
        """
        pass
    
    def create_error_context(self, 
                           component: str, 
                           operation: str, 
                           error: Exception,
                           **kwargs) -> ErrorContext:
        """
        Create error context for tracking.
        
        Args:
            component: Component where error occurred
            operation: Operation that failed
            error: The exception that occurred
            **kwargs: Additional context data
            
        Returns:
            ErrorContext object
        """
        return ErrorContext(
            component=component,
            operation=operation,
            retry_count=0,
            max_retries=kwargs.get('max_retries', 3),
            fallback_available=kwargs.get('fallback_available', False),
            original_error=error,
            timestamp=datetime.now(),
            context_data=kwargs.get('context_data')
        )
    
    def is_retriable_error(self, error: Exception) -> bool:
        """
        Check if error is generally retriable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error type is generally retriable
        """
        retriable_categories = [
            ErrorCategory.NETWORK,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RESOURCE
        ]
        return self.classify_error(error) in retriable_categories