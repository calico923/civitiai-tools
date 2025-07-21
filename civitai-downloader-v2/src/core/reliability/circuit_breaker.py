#!/usr/bin/env python3
"""
Circuit Breaker Pattern Implementation.
Implements requirement 17.4: Staged degradation for reliability.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Circuit is open, calls fail fast
    HALF_OPEN = "half_open" # Testing if service has recovered


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics."""
    total_requests: int = 0
    failed_requests: int = 0
    success_requests: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    response_times: list = field(default_factory=list)
    state_changes: list = field(default_factory=list)
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
    
    @property
    def success_rate(self) -> float:
        """Calculate current success rate."""
        return 1.0 - self.failure_rate
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times[-100:])  # Last 100 requests


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, message: str, circuit_name: str, state: CircuitState):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.state = state


class CircuitBreaker:
    """
    Circuit breaker implementation for reliability.
    Implements requirement 17.1: 90% fallback success rate.
    """
    
    def __init__(self,
                 name: str,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception,
                 success_threshold: int = 3):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            recovery_timeout: Time in seconds before trying half-open
            expected_exception: Exception type to consider as failure
            success_threshold: Successful calls needed to close from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        
        # Callbacks
        self.on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None
        self.on_failure: Optional[Callable[[Exception], None]] = None
        self.on_success: Optional[Callable[[float], None]] = None
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                self.metrics.total_requests += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN",
                    self.name,
                    self.state
                )
        
        start_time = time.time()
        self.metrics.total_requests += 1
        
        try:
            result = await func(*args, **kwargs)
            
            # Record success
            response_time = time.time() - start_time
            await self._record_success(response_time)
            
            return result
            
        except self.expected_exception as e:
            # Record failure
            await self._record_failure(e)
            raise
        
        except Exception as e:
            # Unexpected exception - don't count as failure
            logger.warning(f"Unexpected exception in circuit breaker '{self.name}': {e}")
            raise
    
    async def _record_success(self, response_time: float) -> None:
        """Record successful call."""
        current_time = time.time()
        
        self.metrics.success_requests += 1
        self.metrics.last_success_time = current_time
        self.metrics.response_times.append(response_time)
        
        # Keep only recent response times
        if len(self.metrics.response_times) > 1000:
            self.metrics.response_times = self.metrics.response_times[-1000:]
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                await self._transition_to_closed()
        
        # Callback
        if self.on_success:
            try:
                self.on_success(response_time)
            except Exception as e:
                logger.error(f"Error in success callback: {e}")
    
    async def _record_failure(self, exception: Exception) -> None:
        """Record failed call."""
        current_time = time.time()
        
        self.metrics.failed_requests += 1
        self.metrics.last_failure_time = current_time
        self.last_failure_time = current_time
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                await self._transition_to_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            await self._transition_to_open()
        
        # Callback
        if self.on_failure:
            try:
                self.on_failure(exception)
            except Exception as e:
                logger.error(f"Error in failure callback: {e}")
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset circuit breaker."""
        if self.last_failure_time is None:
            return False
        
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    async def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.failure_count = 0
        self.success_count = 0
        
        self.metrics.state_changes.append({
            'from': old_state.value,
            'to': self.state.value,
            'timestamp': time.time(),
            'failure_rate': self.metrics.failure_rate
        })
        
        logger.warning(f"Circuit breaker '{self.name}' opened (failure rate: {self.metrics.failure_rate:.2%})")
        
        if self.on_state_change:
            try:
                self.on_state_change(old_state, self.state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        
        self.metrics.state_changes.append({
            'from': old_state.value,
            'to': self.state.value,
            'timestamp': time.time()
        })
        
        logger.info(f"Circuit breaker '{self.name}' is now HALF_OPEN (testing recovery)")
        
        if self.on_state_change:
            try:
                self.on_state_change(old_state, self.state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    async def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        
        self.metrics.state_changes.append({
            'from': old_state.value,
            'to': self.state.value,
            'timestamp': time.time(),
            'success_rate': self.metrics.success_rate
        })
        
        logger.info(f"Circuit breaker '{self.name}' closed (service recovered)")
        
        if self.on_state_change:
            try:
                self.on_state_change(old_state, self.state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            'name': self.name,
            'state': self.state.value,
            'total_requests': self.metrics.total_requests,
            'failed_requests': self.metrics.failed_requests,
            'success_requests': self.metrics.success_requests,
            'failure_rate': self.metrics.failure_rate,
            'success_rate': self.metrics.success_rate,
            'average_response_time': self.metrics.average_response_time,
            'failure_threshold': self.failure_threshold,
            'recovery_timeout': self.recovery_timeout,
            'current_failure_count': self.failure_count,
            'state_changes': len(self.metrics.state_changes),
            'last_failure_time': self.metrics.last_failure_time,
            'last_success_time': self.metrics.last_success_time
        }
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        
        if self.on_state_change:
            try:
                self.on_state_change(old_state, self.state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def create_circuit_breaker(self,
                             name: str,
                             failure_threshold: int = 5,
                             recovery_timeout: int = 60,
                             expected_exception: type = Exception,
                             success_threshold: int = 3) -> CircuitBreaker:
        """
        Create and register a circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            recovery_timeout: Time in seconds before trying half-open
            expected_exception: Exception type to consider as failure
            success_threshold: Successful calls needed to close from half-open
            
        Returns:
            CircuitBreaker instance
        """
        circuit_breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold
        )
        
        self.circuit_breakers[name] = circuit_breaker
        logger.info(f"Created circuit breaker: {name}")
        
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all circuit breakers."""
        return {
            'circuit_breakers': {
                name: cb.get_metrics()
                for name, cb in self.circuit_breakers.items()
            },
            'summary': {
                'total_circuits': len(self.circuit_breakers),
                'open_circuits': len([cb for cb in self.circuit_breakers.values() if cb.state == CircuitState.OPEN]),
                'half_open_circuits': len([cb for cb in self.circuit_breakers.values() if cb.state == CircuitState.HALF_OPEN]),
                'closed_circuits': len([cb for cb in self.circuit_breakers.values() if cb.state == CircuitState.CLOSED])
            }
        }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.reset()
        
        logger.info("All circuit breakers reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all circuit breakers."""
        health_status = {
            'healthy': True,
            'details': {}
        }
        
        for name, circuit_breaker in self.circuit_breakers.items():
            cb_metrics = circuit_breaker.get_metrics()
            
            # Consider circuit unhealthy if open or high failure rate
            is_healthy = (
                circuit_breaker.state != CircuitState.OPEN and
                cb_metrics['failure_rate'] < 0.5
            )
            
            health_status['details'][name] = {
                'healthy': is_healthy,
                'state': cb_metrics['state'],
                'failure_rate': cb_metrics['failure_rate'],
                'total_requests': cb_metrics['total_requests']
            }
            
            if not is_healthy:
                health_status['healthy'] = False
        
        return health_status