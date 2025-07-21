#!/usr/bin/env python3
"""
Enhanced Error Handler for Phase 5.
Implements comprehensive error handling per requirement 8 with intelligent backoff,
detailed logging, performance tracking, and advanced recovery mechanisms.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import random
import statistics

from .unified_error_handler import UnifiedErrorHandler, UnifiedError, ErrorCategory, RecoveryStrategy
from .error_context import ErrorContext


class LogLevel(Enum):
    """Logging levels per requirement 8.3."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BackoffStrategy(Enum):
    """Intelligent backoff strategies per requirement 8.2."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"
    ADAPTIVE = "adaptive"
    JITTERED = "jittered"


@dataclass
class RetryMetrics:
    """Retry performance metrics."""
    attempt_number: int
    timestamp: float
    delay_seconds: float
    error_type: str
    success: bool
    response_time: Optional[float] = None
    backoff_strategy: Optional[str] = None


@dataclass
class ErrorMetrics:
    """Comprehensive error metrics per requirement 8.6."""
    api_usage: Dict[str, int]
    timing_data: Dict[str, List[float]]
    success_rates: Dict[str, float]
    error_patterns: Dict[str, int]
    backoff_effectiveness: Dict[str, float]
    recovery_success_rates: Dict[str, float]
    performance_impact: Dict[str, float]


class EnhancedErrorHandler(UnifiedErrorHandler):
    """
    Enhanced error handler implementing requirement 8.
    
    Provides:
    - Intelligent backoff and retry (8.2)
    - Multi-level logging (8.3) 
    - Detailed error handling for network, auth, parsing (8.4)
    - Request/response logging (8.5)
    - API usage and performance tracking (8.6)
    """
    
    def wrap_error(self, error: Exception, context: Dict[str, Any]) -> UnifiedError:
        """Override parent to track metrics only for top-level errors."""
        unified_error = super().wrap_error(error, context)
        
        # Update error metrics for enhancement tracking (avoid double counting in retry loops)
        if not hasattr(error, '_tracked_by_enhanced_handler'):
            operation_key = f"{context.get('component', 'unknown')}.{context.get('operation', 'unknown')}"
            self._update_error_metrics(operation_key, unified_error, 0.0)
            error._tracked_by_enhanced_handler = True
        
        return unified_error
    
    def __init__(self, log_level: LogLevel = LogLevel.INFO, 
                 enable_detailed_logging: bool = False,
                 analytics_collector=None):
        """Initialize enhanced error handler."""
        super().__init__()
        self.log_level = log_level
        self.enable_detailed_logging = enable_detailed_logging
        self.analytics_collector = analytics_collector
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Retry and backoff tracking
        self.retry_history: Dict[str, List[RetryMetrics]] = {}
        self.adaptive_delays: Dict[str, float] = {}
        
        # Performance and metrics tracking
        self.metrics = ErrorMetrics(
            api_usage={},
            timing_data={},
            success_rates={},
            error_patterns={},
            backoff_effectiveness={},
            recovery_success_rates={},
            performance_impact={}
        )
        
        # Advanced recovery handlers
        self.recovery_handlers: Dict[ErrorCategory, Callable] = self._setup_recovery_handlers()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup multi-level logging per requirement 8.3."""
        logger = logging.getLogger('civitai_downloader.error_handler')
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Set logging level based on configuration
        level_map = {
            LogLevel.TRACE: logging.DEBUG,
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
        logger.setLevel(level_map[self.log_level])
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # File handler for detailed logging
        if self.enable_detailed_logging:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(log_dir / "error_handler.log")
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
        
        return logger
    
    def _setup_recovery_handlers(self) -> Dict[ErrorCategory, Callable]:
        """Setup specialized recovery handlers per requirement 8.4."""
        return {
            ErrorCategory.NETWORK: self._handle_network_error,
            ErrorCategory.API: self._handle_api_error,
            ErrorCategory.RATE_LIMIT: self._handle_rate_limit_error,
            ErrorCategory.AUTHENTICATION: self._handle_authentication_error,
            ErrorCategory.AUTHORIZATION: self._handle_authorization_error,
            ErrorCategory.NOT_FOUND: self._handle_not_found_error,
            ErrorCategory.VALIDATION: self._handle_validation_error,
            ErrorCategory.SYSTEM: self._handle_system_error
        }
    
    async def execute_with_intelligent_retry(self,
                                           operation: Callable,
                                           context: Dict[str, Any],
                                           max_retries: Optional[int] = None,
                                           backoff_strategy: BackoffStrategy = BackoffStrategy.ADAPTIVE,
                                           *args, **kwargs) -> Any:
        """
        Execute operation with intelligent retry and backoff per requirement 8.2.
        
        Args:
            operation: Function to execute
            context: Error context information
            max_retries: Maximum retry attempts (overrides config)
            backoff_strategy: Backoff strategy to use
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of the successful operation
            
        Raises:
            UnifiedError: If all retry attempts fail
        """
        operation_key = f"{context.get('component', 'unknown')}.{context.get('operation', 'unknown')}"
        
        # Initialize retry tracking
        if operation_key not in self.retry_history:
            self.retry_history[operation_key] = []
        
        attempt = 0
        last_error = None
        start_time = time.time()
        
        while True:
            attempt += 1
            attempt_start = time.time()
            
            try:
                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Record successful attempt
                response_time = time.time() - attempt_start
                self._record_retry_metrics(
                    operation_key, attempt, 0.0, "success", True, 
                    response_time, backoff_strategy.value
                )
                
                # Update success metrics
                self._update_success_metrics(operation_key, True, response_time)
                
                # Log success if there were previous failures
                if attempt > 1:
                    self.logger.info(
                        f"Operation {operation_key} succeeded on attempt {attempt} "
                        f"after {time.time() - start_time:.2f}s"
                    )
                
                return result
                
            except Exception as e:
                last_error = e
                
                # Wrap error with context
                unified_error = self.wrap_error(e, context)
                
                # Update error metrics
                self._update_error_metrics(operation_key, unified_error, time.time() - attempt_start)
                
                # Check if we should retry
                should_retry, delay = self._should_retry_operation(
                    unified_error, attempt, max_retries, backoff_strategy, operation_key
                )
                
                if not should_retry:
                    self.logger.error(
                        f"Operation {operation_key} failed after {attempt} attempts: {unified_error.log_message}"
                    )
                    raise unified_error.original_error
                
                # Record failed attempt
                self._record_retry_metrics(
                    operation_key, attempt, delay, type(e).__name__, False, 
                    time.time() - attempt_start, backoff_strategy.value
                )
                
                # Log retry attempt
                self.logger.warning(
                    f"Operation {operation_key} failed on attempt {attempt}/{max_retries or 'unlimited'}: "
                    f"{unified_error.user_message}. Retrying in {delay:.2f}s"
                )
                
                # Wait before retry
                if delay > 0:
                    await asyncio.sleep(delay)
    
    def _should_retry_operation(self, unified_error: UnifiedError, attempt: int,
                              max_retries: Optional[int], backoff_strategy: BackoffStrategy,
                              operation_key: str) -> Tuple[bool, float]:
        """Determine if operation should be retried and calculate delay."""
        # Check if error is retryable
        if not unified_error.is_retryable:
            return False, 0.0
        
        # Check max retries
        config_max_retries = unified_error.recovery_config.max_retries
        effective_max_retries = max_retries if max_retries is not None else config_max_retries
        
        if attempt > effective_max_retries:
            return False, 0.0
        
        # Calculate delay based on strategy
        delay = self._calculate_backoff_delay(
            unified_error, attempt, backoff_strategy, operation_key
        )
        
        return True, delay
    
    def _calculate_backoff_delay(self, unified_error: UnifiedError, attempt: int,
                               backoff_strategy: BackoffStrategy, operation_key: str) -> float:
        """Calculate intelligent backoff delay per requirement 8.2."""
        config = unified_error.recovery_config
        base_delay = config.initial_delay
        
        if backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = base_delay * (config.backoff_multiplier ** (attempt - 1))
            
        elif backoff_strategy == BackoffStrategy.LINEAR:
            delay = base_delay * attempt
            
        elif backoff_strategy == BackoffStrategy.FIBONACCI:
            fib_sequence = self._fibonacci(attempt + 1)
            delay = base_delay * fib_sequence
            
        elif backoff_strategy == BackoffStrategy.ADAPTIVE:
            # Use historical success rates to adapt delay
            delay = self._calculate_adaptive_delay(operation_key, attempt, base_delay, config)
            
        elif backoff_strategy == BackoffStrategy.JITTERED:
            # Exponential with jitter to avoid thundering herd
            base_exponential = base_delay * (config.backoff_multiplier ** (attempt - 1))
            jitter = random.uniform(0.5, 1.5)
            delay = base_exponential * jitter
        
        else:
            delay = base_delay
        
        # Apply max delay limit
        delay = min(delay, config.max_delay)
        
        # Add rate limit specific handling
        if unified_error.error_category == ErrorCategory.RATE_LIMIT:
            # For rate limits, use longer delays
            delay = max(delay, 5.0)
        
        return delay
    
    def _calculate_adaptive_delay(self, operation_key: str, attempt: int, 
                                base_delay: float, config) -> float:
        """Calculate adaptive delay based on historical performance."""
        if operation_key not in self.retry_history:
            return base_delay
        
        history = self.retry_history[operation_key]
        if len(history) < 3:  # Need some history for adaptation
            return base_delay * (config.backoff_multiplier ** (attempt - 1))
        
        # Calculate success rate for recent attempts
        recent_history = history[-10:]  # Last 10 attempts
        success_rate = sum(1 for metric in recent_history if metric.success) / len(recent_history)
        
        # Adjust delay based on success rate
        if success_rate > 0.8:
            # High success rate, reduce delay
            multiplier = 0.7
        elif success_rate > 0.5:
            # Medium success rate, normal delay
            multiplier = 1.0
        else:
            # Low success rate, increase delay
            multiplier = 1.5
        
        # Calculate average response time for successful attempts
        successful_times = [m.response_time for m in recent_history 
                          if m.success and m.response_time]
        if successful_times:
            avg_response_time = statistics.mean(successful_times)
            # If responses are slow, increase delay
            if avg_response_time > 5.0:
                multiplier *= 1.2
        
        delay = base_delay * (config.backoff_multiplier ** (attempt - 1)) * multiplier
        return delay
    
    def _fibonacci(self, n: int) -> int:
        """Calculate Fibonacci number for backoff strategy."""
        if n <= 1:
            return n
        return self._fibonacci(n-1) + self._fibonacci(n-2)
    
    def _record_retry_metrics(self, operation_key: str, attempt: int, delay: float,
                             error_type: str, success: bool, response_time: Optional[float],
                             backoff_strategy: str) -> None:
        """Record retry metrics for analysis."""
        metric = RetryMetrics(
            attempt_number=attempt,
            timestamp=time.time(),
            delay_seconds=delay,
            error_type=error_type,
            success=success,
            response_time=response_time,
            backoff_strategy=backoff_strategy
        )
        
        # Ensure operation key exists in retry history
        if operation_key not in self.retry_history:
            self.retry_history[operation_key] = []
        
        self.retry_history[operation_key].append(metric)
        
        # Limit history size
        if len(self.retry_history[operation_key]) > 100:
            self.retry_history[operation_key] = self.retry_history[operation_key][-50:]
    
    def _update_success_metrics(self, operation_key: str, success: bool, response_time: float) -> None:
        """Update success rate and timing metrics."""
        # Update API usage count
        if operation_key not in self.metrics.api_usage:
            self.metrics.api_usage[operation_key] = 0
        self.metrics.api_usage[operation_key] += 1
        
        # Update timing data
        if operation_key not in self.metrics.timing_data:
            self.metrics.timing_data[operation_key] = []
        self.metrics.timing_data[operation_key].append(response_time)
        
        # Limit timing data size
        if len(self.metrics.timing_data[operation_key]) > 100:
            self.metrics.timing_data[operation_key] = self.metrics.timing_data[operation_key][-50:]
        
        # Update success rates
        if operation_key not in self.metrics.success_rates:
            self.metrics.success_rates[operation_key] = 0.0
        
        # Calculate rolling success rate
        recent_history = self.retry_history.get(operation_key, [])[-20:]  # Last 20 attempts
        if recent_history:
            successful_attempts = sum(1 for metric in recent_history if metric.success)
            self.metrics.success_rates[operation_key] = successful_attempts / len(recent_history)
    
    def _update_error_metrics(self, operation_key: str, unified_error: UnifiedError, response_time: float) -> None:
        """Update error pattern metrics."""
        error_type = type(unified_error.original_error).__name__
        
        # Update error patterns  
        pattern_key = f"{operation_key}.{error_type}"
        if pattern_key not in self.metrics.error_patterns:
            self.metrics.error_patterns[pattern_key] = 0
        self.metrics.error_patterns[pattern_key] += 1
        
        # Update performance impact
        if operation_key not in self.metrics.performance_impact:
            self.metrics.performance_impact[operation_key] = 0.0
        
        # Calculate performance impact based on error frequency
        total_calls = self.metrics.api_usage.get(operation_key, 1)
        error_count = sum(count for key, count in self.metrics.error_patterns.items() 
                         if key.startswith(operation_key))
        self.metrics.performance_impact[operation_key] = error_count / total_calls
    
    async def log_request_response(self, request_data: Dict[str, Any], 
                                  response_data: Optional[Dict[str, Any]] = None,
                                  error: Optional[Exception] = None,
                                  context: Optional[Dict[str, Any]] = None) -> None:
        """
        Detailed request/response logging per requirement 8.5.
        
        Args:
            request_data: Request information
            response_data: Response data (if successful)
            error: Error information (if failed)
            context: Additional context
        """
        if not self.enable_detailed_logging:
            return
        
        log_entry = {
            "timestamp": time.time(),
            "request": {
                "method": request_data.get("method", "unknown"),
                "endpoint": request_data.get("endpoint", "unknown"),
                "parameters": request_data.get("parameters", {}),
                "headers": request_data.get("headers", {}),
                "size": request_data.get("size", 0)
            }
        }
        
        if response_data:
            log_entry["response"] = {
                "status_code": response_data.get("status_code"),
                "size": response_data.get("size", 0),
                "response_time": response_data.get("response_time", 0),
                "headers": response_data.get("headers", {}),
                "data_preview": str(response_data.get("data", ""))[:200] + "..." if response_data.get("data") else None
            }
            log_entry["status"] = "success"
        
        if error:
            unified_error = self.wrap_error(error, context or {})
            log_entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "category": unified_error.error_category.value,
                "is_retryable": unified_error.is_retryable,
                "suggested_action": unified_error.suggested_action
            }
            log_entry["status"] = "error"
        
        if context:
            log_entry["context"] = context
        
        # Log with appropriate level
        if error:
            self.logger.error(f"API Call Failed: {json.dumps(log_entry, default=str, indent=2)}")
        else:
            self.logger.debug(f"API Call Successful: {json.dumps(log_entry, default=str, indent=2)}")
        
        # Send to analytics collector if available
        if self.analytics_collector:
            if error:
                self.analytics_collector.record_api_error(
                    request_id=context.get("request_id", "unknown"),
                    error_type=type(error).__name__,
                    error_message=str(error)
                )
            else:
                self.analytics_collector.record_api_response(
                    request_id=context.get("request_id", "unknown"),
                    status_code=response_data.get("status_code", 200),
                    response_time=response_data.get("response_time", 0),
                    response_size=response_data.get("size", 0)
                )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance and error report per requirement 8.6.
        
        Returns:
            Performance metrics and analytics
        """
        report = {
            "timestamp": time.time(),
            "api_usage_stats": dict(self.metrics.api_usage),
            "success_rates": dict(self.metrics.success_rates),
            "error_patterns": dict(self.metrics.error_patterns),
            "performance_impact": dict(self.metrics.performance_impact),
            "timing_statistics": {},
            "retry_effectiveness": {},
            "recommendations": []
        }
        
        # Calculate timing statistics
        for operation, times in self.metrics.timing_data.items():
            if times:
                report["timing_statistics"][operation] = {
                    "avg_response_time": statistics.mean(times),
                    "min_response_time": min(times),
                    "max_response_time": max(times),
                    "median_response_time": statistics.median(times),
                    "total_calls": len(times)
                }
        
        # Calculate retry effectiveness
        for operation, history in self.retry_history.items():
            if history:
                retry_attempts = [h for h in history if h.attempt_number > 1]
                if retry_attempts:
                    successful_retries = [h for h in retry_attempts if h.success]
                    report["retry_effectiveness"][operation] = {
                        "total_retries": len(retry_attempts),
                        "successful_retries": len(successful_retries),
                        "retry_success_rate": len(successful_retries) / len(retry_attempts),
                        "avg_attempts_to_success": statistics.mean([h.attempt_number for h in successful_retries]) if successful_retries else 0
                    }
        
        # Generate recommendations
        recommendations = []
        
        # Check for operations with low success rates
        for operation, success_rate in self.metrics.success_rates.items():
            if success_rate < 0.8:
                recommendations.append(f"Operation '{operation}' has low success rate ({success_rate:.1%}). Consider reviewing API parameters or rate limits.")
        
        # Check for operations with high response times
        for operation, stats in report["timing_statistics"].items():
            if stats["avg_response_time"] > 10.0:
                recommendations.append(f"Operation '{operation}' has high average response time ({stats['avg_response_time']:.2f}s). Consider optimizing requests.")
        
        # Check for frequent error patterns
        total_errors = sum(self.metrics.error_patterns.values())
        if total_errors > 0:
            most_common_error = max(self.metrics.error_patterns.items(), key=lambda x: x[1])
            if most_common_error[1] > total_errors * 0.3:
                recommendations.append(f"Most common error pattern '{most_common_error[0]}' accounts for {most_common_error[1]/total_errors:.1%} of all errors. Focus on resolving this issue.")
        
        report["recommendations"] = recommendations
        
        return report
    
    # Specialized error handlers per requirement 8.4
    
    async def _handle_network_error(self, unified_error: UnifiedError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle network errors with intelligent retry."""
        return {
            "strategy": "retry_with_backoff",
            "max_retries": 5,
            "backoff_strategy": BackoffStrategy.EXPONENTIAL,
            "user_message": "Network connection issue. Retrying with intelligent backoff...",
            "details": "Network errors are typically transient and benefit from exponential backoff"
        }
    
    async def _handle_api_error(self, unified_error: UnifiedError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API-specific errors."""
        return {
            "strategy": "retry_with_analysis",
            "max_retries": 3,
            "backoff_strategy": BackoffStrategy.ADAPTIVE,
            "user_message": "API service issue. Analyzing and retrying...",
            "details": f"API error: {unified_error.original_error}"
        }
    
    async def _handle_rate_limit_error(self, unified_error: UnifiedError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rate limit errors with extended backoff."""
        return {
            "strategy": "extended_backoff",
            "max_retries": 10,
            "backoff_strategy": BackoffStrategy.JITTERED,
            "user_message": "Rate limit reached. Waiting with extended backoff...",
            "details": "Rate limits require longer wait times and jittered backoff to avoid thundering herd"
        }
    
    async def _handle_authentication_error(self, unified_error: UnifiedError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authentication errors."""
        return {
            "strategy": "user_intervention",
            "max_retries": 0,
            "user_message": "Authentication failed. Please verify your API credentials.",
            "details": "Authentication errors typically require user intervention to resolve"
        }
    
    async def _handle_authorization_error(self, unified_error: UnifiedError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authorization errors."""
        return {
            "strategy": "abort",
            "max_retries": 0,
            "user_message": "Access denied. You don't have permission for this operation.",
            "details": "Authorization errors cannot be resolved by retrying"
        }
    
    async def _handle_not_found_error(self, unified_error: UnifiedError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle not found errors with fallback options."""
        return {
            "strategy": "fallback_or_abort",
            "max_retries": 1,
            "user_message": "Resource not found. Trying alternative approaches...",
            "details": "Not found errors may benefit from fallback strategies"
        }
    
    async def _handle_validation_error(self, unified_error: UnifiedError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validation errors."""
        return {
            "strategy": "abort",
            "max_retries": 0,
            "user_message": f"Invalid input: {unified_error.original_error}",
            "details": "Validation errors require fixing the input, not retrying"
        }
    
    async def _handle_system_error(self, unified_error: UnifiedError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system-level errors."""
        return {
            "strategy": "retry_limited",
            "max_retries": 2,
            "backoff_strategy": BackoffStrategy.LINEAR,
            "user_message": "System error encountered. Attempting limited retry...",
            "details": "System errors may be transient but shouldn't be retried extensively"
        }