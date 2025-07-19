"""
UnifiedErrorHandler - Comprehensive error handling system.

This module provides unified error handling with categorization, fallback mechanisms,
context tracking, and comprehensive error reporting capabilities.
"""

import asyncio
import uuid
import traceback
import time
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass
from enum import Enum

import sys
from pathlib import Path

# Add the src directory to the path for importing
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from core.error.error_context import ErrorContext
from core.error.error_statistics import ErrorStatistics
from core.error.api_errors import (
    APIError, APIRateLimitError, APIAuthenticationError, APIAuthorizationError,
    APINotFoundError, APIValidationError, APIServerError, APIUnavailableError,
    APIConnectionError, APITimeoutError, APIResponseError, APIDeprecatedError
)


class ErrorCategory(Enum):
    """Error category classification."""
    NETWORK = "NETWORK"
    API = "API"
    VALIDATION = "VALIDATION"
    SYSTEM = "SYSTEM"
    RATE_LIMIT = "RATE_LIMIT"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"


class RecoveryStrategy(Enum):
    """Error recovery strategy types."""
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    ABORT = "ABORT"
    USER_INPUT = "USER_INPUT"


@dataclass
class RecoveryConfig:
    """Configuration for error recovery."""
    strategy: RecoveryStrategy
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True


@dataclass
class UnifiedError:
    """Unified error wrapper with comprehensive context."""
    error_id: str
    original_error: Exception
    error_context: ErrorContext
    error_category: ErrorCategory
    suggested_action: str
    recovery_config: RecoveryConfig
    timestamp: float
    user_message: str
    log_message: str
    is_user_facing: bool = True
    is_retryable: bool = False


class UnifiedErrorHandler:
    """
    Comprehensive unified error handling system.
    
    This class provides centralized error handling with categorization,
    fallback mechanisms, statistical tracking, and consistent error reporting.
    """
    
    def __init__(self):
        """Initialize the unified error handler."""
        self.error_statistics = ErrorStatistics()
        self.fallback_services = {}
        self.recovery_configs = self._setup_default_recovery_configs()
        self.error_callbacks = []
    
    def _setup_default_recovery_configs(self) -> Dict[ErrorCategory, RecoveryConfig]:
        """Setup default recovery configurations for different error categories."""
        return {
            ErrorCategory.NETWORK: RecoveryConfig(
                strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                backoff_multiplier=2.0,
                initial_delay=1.0
            ),
            ErrorCategory.API: RecoveryConfig(
                strategy=RecoveryStrategy.RETRY,
                max_retries=2,
                backoff_multiplier=1.5,
                initial_delay=0.5
            ),
            ErrorCategory.RATE_LIMIT: RecoveryConfig(
                strategy=RecoveryStrategy.RETRY,
                max_retries=5,
                backoff_multiplier=3.0,
                initial_delay=5.0,
                max_delay=300.0
            ),
            ErrorCategory.VALIDATION: RecoveryConfig(
                strategy=RecoveryStrategy.ABORT,
                max_retries=0
            ),
            ErrorCategory.AUTHENTICATION: RecoveryConfig(
                strategy=RecoveryStrategy.USER_INPUT,
                max_retries=0
            ),
            ErrorCategory.AUTHORIZATION: RecoveryConfig(
                strategy=RecoveryStrategy.ABORT,
                max_retries=0
            ),
            ErrorCategory.NOT_FOUND: RecoveryConfig(
                strategy=RecoveryStrategy.FALLBACK,
                max_retries=1
            ),
            ErrorCategory.SYSTEM: RecoveryConfig(
                strategy=RecoveryStrategy.RETRY,
                max_retries=1,
                initial_delay=2.0
            ),
            ErrorCategory.UNKNOWN: RecoveryConfig(
                strategy=RecoveryStrategy.RETRY,
                max_retries=1,
                initial_delay=1.0
            )
        }
    
    def wrap_error(self, error: Exception, context: Dict[str, Any]) -> UnifiedError:
        """
        Wrap an error with unified error structure.
        
        Args:
            error: Original exception
            context: Error context information
            
        Returns:
            UnifiedError with comprehensive error information
        """
        # Create error context
        if isinstance(context, dict):
            # Extract known context fields
            parameters = context.get('parameters', {})
            # Add any additional context data to parameters
            for key, value in context.items():
                if key not in ['operation', 'component', 'endpoint', 'parameters', 'request_id']:
                    parameters[key] = value
            
            error_context = ErrorContext(
                operation=context.get('operation', 'unknown'),
                component=context.get('component', 'unknown'),
                endpoint=context.get('endpoint'),
                parameters=parameters,
                request_id=context.get('request_id', str(uuid.uuid4())),
                timestamp=time.time()
            )
        else:
            error_context = context
        
        # Categorize error
        category = self.categorize_error(error)
        
        # Get recovery configuration
        recovery_config = self.recovery_configs.get(category, self.recovery_configs[ErrorCategory.UNKNOWN])
        
        # Generate messages
        user_message = self._generate_user_message(error, category, error_context)
        log_message = self._generate_log_message(error, category, error_context)
        suggested_action = self._generate_suggested_action(error, category, recovery_config)
        
        # Record error statistics
        self.error_statistics.record_error(
            category=category.value,
            error_type=type(error).__name__,
            component=error_context.component,
            operation=error_context.operation,
            message=str(error),
            context=error_context.to_dict()
        )
        
        # Create unified error
        unified_error = UnifiedError(
            error_id=str(uuid.uuid4()),
            original_error=error,
            error_context=error_context,
            error_category=category,
            suggested_action=suggested_action,
            recovery_config=recovery_config,
            timestamp=time.time(),
            user_message=user_message,
            log_message=log_message,
            is_user_facing=error_context.is_user_facing(),
            is_retryable=recovery_config.strategy in [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK]
        )
        
        # Notify callbacks
        for callback in self.error_callbacks:
            try:
                callback(unified_error)
            except Exception:
                # Don't let callback errors break error handling
                pass
        
        return unified_error
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize error based on type and attributes.
        
        Args:
            error: Exception to categorize
            
        Returns:
            ErrorCategory for the error
        """
        # API-specific errors
        if isinstance(error, APIRateLimitError):
            return ErrorCategory.RATE_LIMIT
        elif isinstance(error, APIAuthenticationError):
            return ErrorCategory.AUTHENTICATION
        elif isinstance(error, APIAuthorizationError):
            return ErrorCategory.AUTHORIZATION
        elif isinstance(error, APINotFoundError):
            return ErrorCategory.NOT_FOUND
        elif isinstance(error, APIError):
            return ErrorCategory.API
        
        # Network errors
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK
        
        # Permission/Authorization errors  
        elif isinstance(error, PermissionError):
            return ErrorCategory.AUTHORIZATION
        
        # Validation errors
        elif isinstance(error, (ValueError, TypeError)):
            return ErrorCategory.VALIDATION
        
        # System errors
        elif isinstance(error, (OSError, IOError, MemoryError)):
            return ErrorCategory.SYSTEM
        
        # Default
        else:
            return ErrorCategory.UNKNOWN
    
    def get_recovery_strategy(self, error: Exception) -> Dict[str, Any]:
        """
        Get recovery strategy for an error.
        
        Args:
            error: Exception to get strategy for
            
        Returns:
            Recovery strategy configuration
        """
        category = self.categorize_error(error)
        config = self.recovery_configs.get(category, self.recovery_configs[ErrorCategory.UNKNOWN])
        
        return {
            'type': config.strategy.value,
            'max_retries': config.max_retries,
            'backoff_multiplier': config.backoff_multiplier,
            'initial_delay': config.initial_delay,
            'max_delay': config.max_delay
        }
    
    def register_fallback(self, service_name: str, primary_service: Any, fallback_service: Any) -> None:
        """
        Register a fallback service for a primary service.
        
        Args:
            service_name: Name of the service
            primary_service: Primary service instance
            fallback_service: Fallback service instance
        """
        self.fallback_services[service_name] = {
            'primary': primary_service,
            'fallback': fallback_service
        }
    
    def execute_with_fallback(self, service_name: str, operation: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute operation with fallback capability.
        
        Args:
            service_name: Name of the service
            operation: Operation to execute
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of the operation with fallback information
        """
        if service_name not in self.fallback_services:
            raise ValueError(f"No fallback configured for service: {service_name}")
        
        services = self.fallback_services[service_name]
        primary = services['primary']
        fallback = services['fallback']
        
        # Try primary service first
        try:
            result = getattr(primary, operation)(*args, **kwargs)
            return {
                'status': 'success',
                'data': result,
                'used_fallback': False,
                'service': 'primary'
            }
        except Exception as e:
            # Record primary failure
            self.error_statistics.record_error(
                category=self.categorize_error(e).value,
                error_type=type(e).__name__,
                component=service_name,
                operation=operation,
                message=f"Primary service failed: {str(e)}"
            )
            
            # Try fallback service
            try:
                result = getattr(fallback, operation)(*args, **kwargs)
                return {
                    'status': 'success',
                    'data': result,
                    'used_fallback': True,
                    'service': 'fallback',
                    'primary_error': str(e)
                }
            except Exception as fallback_error:
                # Both services failed
                self.error_statistics.record_error(
                    category=self.categorize_error(fallback_error).value,
                    error_type=type(fallback_error).__name__,
                    component=service_name,
                    operation=operation,
                    message=f"Fallback service also failed: {str(fallback_error)}"
                )
                
                # Re-raise the original error
                raise e
    
    async def handle_async_error(self, awaitable, context: Dict[str, Any]):
        """
        Handle errors in async operations.
        
        Args:
            awaitable: Async operation to execute
            context: Error context
            
        Returns:
            Result of the operation
            
        Raises:
            UnifiedError: Wrapped error with context
        """
        try:
            return await awaitable
        except Exception as e:
            unified_error = self.wrap_error(e, context)
            # Re-raise as the original exception but with added context attribute
            e.error_context = unified_error.error_context
            raise e
    
    def format_user_message(self, unified_error: UnifiedError) -> str:
        """
        Format user-friendly error message.
        
        Args:
            unified_error: Unified error to format
            
        Returns:
            User-friendly error message
        """
        return unified_error.user_message
    
    def format_log_message(self, unified_error: UnifiedError) -> str:
        """
        Format detailed log message.
        
        Args:
            unified_error: Unified error to format
            
        Returns:
            Detailed log message
        """
        return unified_error.log_message
    
    def format_structured_data(self, unified_error: UnifiedError) -> Dict[str, Any]:
        """
        Format error as structured data for logging systems.
        
        Args:
            unified_error: Unified error to format
            
        Returns:
            Structured error data
        """
        return {
            'error_id': unified_error.error_id,
            'timestamp': unified_error.timestamp,
            'category': unified_error.error_category.value,
            'error_type': type(unified_error.original_error).__name__,
            'message': str(unified_error.original_error),
            'context': unified_error.error_context.to_dict(),
            'suggested_action': unified_error.suggested_action,
            'is_retryable': unified_error.is_retryable,
            'recovery_strategy': unified_error.recovery_config.strategy.value,
            'stack_trace': traceback.format_exception(
                type(unified_error.original_error),
                unified_error.original_error,
                unified_error.original_error.__traceback__
            )
        }
    
    def _generate_user_message(self, error: Exception, category: ErrorCategory, context: ErrorContext) -> str:
        """Generate user-friendly error message."""
        if category == ErrorCategory.NETWORK:
            return "Connection problem. Please check your internet connection and try again."
        elif category == ErrorCategory.API:
            return "Service temporarily unavailable. Please try again in a few moments."
        elif category == ErrorCategory.RATE_LIMIT:
            return "Too many requests. Please wait a moment before trying again."
        elif category == ErrorCategory.AUTHENTICATION:
            return "Authentication failed. Please check your API key and try again."
        elif category == ErrorCategory.AUTHORIZATION:
            return "Access denied. You don't have permission to perform this operation."
        elif category == ErrorCategory.NOT_FOUND:
            return "Requested item not found. It may have been removed or moved."
        elif category == ErrorCategory.VALIDATION:
            return f"Invalid input: {str(error)}"
        elif category == ErrorCategory.SYSTEM:
            return "System error occurred. Please try again or contact support if the problem persists."
        else:
            return "An unexpected error occurred. Please try again."
    
    def _generate_log_message(self, error: Exception, category: ErrorCategory, context: ErrorContext) -> str:
        """Generate detailed log message."""
        return (f"Error in {context.operation} ({context.component}): "
                f"{category.value} - {type(error).__name__}: {str(error)} "
                f"| Context: {context.get_summary()}")
    
    def _generate_suggested_action(self, error: Exception, category: ErrorCategory, 
                                 recovery_config: RecoveryConfig) -> str:
        """Generate suggested action for error recovery."""
        if recovery_config.strategy == RecoveryStrategy.RETRY:
            return f"Retry operation (max {recovery_config.max_retries} attempts)"
        elif recovery_config.strategy == RecoveryStrategy.FALLBACK:
            return "Try alternative method"
        elif recovery_config.strategy == RecoveryStrategy.USER_INPUT:
            return "User intervention required"
        elif recovery_config.strategy == RecoveryStrategy.ABORT:
            return "Operation cannot be completed"
        else:
            return "Contact support if problem persists"