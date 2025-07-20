#!/usr/bin/env python3
"""
Rate Limiter for CivitAI API requests.
Implements rate limiting to respect API usage policies with adaptive adjustment.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import math


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive rate limiting."""
    min_rate: float = 0.1
    max_rate: float = 2.0
    increase_factor: float = 1.05
    decrease_factor: float = 0.8
    success_threshold: int = 10
    error_threshold: int = 3
    adjustment_window: int = 60  # seconds


class RateLimiter:
    """Rate limiter to control API request frequency with adaptive adjustment."""
    
    def __init__(self, requests_per_second: float = 0.5, 
                 adaptive_config: Optional[AdaptiveConfig] = None,
                 min_rate: Optional[float] = None,
                 max_rate: Optional[float] = None):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Initial requests per second allowed
            adaptive_config: Configuration for adaptive behavior
            min_rate: Minimum rate (fallback if no adaptive_config)
            max_rate: Maximum rate (fallback if no adaptive_config)
        """
        self.initial_rate = requests_per_second
        self.current_rate = requests_per_second
        
        # Configure adaptive behavior
        if adaptive_config:
            self.adaptive_config = adaptive_config
        else:
            self.adaptive_config = AdaptiveConfig(
                min_rate=min_rate or 0.1,
                max_rate=max_rate or 2.0
            )
        
        self.min_interval = 1.0 / self.current_rate if self.current_rate > 0 else 0
        self.last_request_time: Optional[datetime] = None
        
        # Adaptive tracking
        self.success_count = 0
        self.error_count = 0
        self.rate_limit_error_count = 0
        self.total_requests = 0
        self.adjustment_history: List[Dict[str, Any]] = []
        self.last_adjustment_time = datetime.now()
        self.burst_detection_enabled = False
        
        # Backward compatibility
        self.requests_per_second = self.current_rate
    
    async def wait(self) -> None:
        """
        Wait if necessary to maintain rate limit.
        """
        current_time = datetime.now()
        
        if self.last_request_time is None:
            # First request, no need to wait
            self.last_request_time = current_time
            return
        
        time_since_last = (current_time - self.last_request_time).total_seconds()
        
        # Update min_interval based on current rate
        self.min_interval = 1.0 / self.current_rate if self.current_rate > 0 else 0
        
        if time_since_last < self.min_interval:
            # Need to wait
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = datetime.now()
        self.total_requests += 1
    
    def record_success(self) -> None:
        """Record a successful request for adaptive rate adjustment."""
        self.success_count += 1
        self._check_and_adjust_rate()
    
    def record_rate_limit_error(self) -> None:
        """Record a rate limit error for adaptive rate adjustment."""
        self.error_count += 1
        self.rate_limit_error_count += 1
        self._check_and_adjust_rate(force_decrease=True)
    
    def record_error(self) -> None:
        """Record a general error for tracking."""
        self.error_count += 1
    
    def get_current_rate(self) -> float:
        """Get the current requests per second rate."""
        return self.current_rate
    
    def adjust_rate(self, new_rate: float) -> None:
        """
        Manually adjust the rate.
        
        Args:
            new_rate: New requests per second rate
        """
        old_rate = self.current_rate
        self.current_rate = max(
            self.adaptive_config.min_rate,
            min(new_rate, self.adaptive_config.max_rate)
        )
        
        if old_rate != self.current_rate:
            self._record_adjustment("manual", old_rate, self.current_rate)
    
    def _check_and_adjust_rate(self, force_decrease: bool = False) -> None:
        """Check if rate should be adjusted based on recent performance."""
        current_time = datetime.now()
        time_since_adjustment = (current_time - self.last_adjustment_time).total_seconds()
        
        # Only adjust if enough time has passed or forced
        if time_since_adjustment < self.adaptive_config.adjustment_window and not force_decrease:
            return
        
        old_rate = self.current_rate
        
        if force_decrease or self.rate_limit_error_count >= self.adaptive_config.error_threshold:
            # Decrease rate due to errors
            self.current_rate *= self.adaptive_config.decrease_factor
            self.current_rate = max(self.current_rate, self.adaptive_config.min_rate)
            self._record_adjustment("decrease_error", old_rate, self.current_rate)
            self._reset_counters()
            
        elif self.success_count >= self.adaptive_config.success_threshold:
            # Increase rate due to successful requests
            self.current_rate *= self.adaptive_config.increase_factor
            self.current_rate = min(self.current_rate, self.adaptive_config.max_rate)
            self._record_adjustment("increase_success", old_rate, self.current_rate)
            self._reset_counters()
    
    def _record_adjustment(self, reason: str, old_rate: float, new_rate: float) -> None:
        """Record a rate adjustment in history."""
        self.adjustment_history.append({
            'timestamp': datetime.now(),
            'event_type': reason,
            'rate_before': old_rate,
            'rate_after': new_rate,
            'success_count': self.success_count,
            'error_count': self.error_count
        })
        self.last_adjustment_time = datetime.now()
        
        # Update backward compatibility property
        self.requests_per_second = self.current_rate
    
    def _reset_counters(self) -> None:
        """Reset success and error counters after adjustment."""
        self.success_count = 0
        self.rate_limit_error_count = 0
        # Keep general error_count for statistics
    
    def get_rate_adjustment_history(self) -> List[Dict[str, Any]]:
        """Get the history of rate adjustments."""
        return self.adjustment_history.copy()
    
    def get_adaptive_config(self) -> Dict[str, Any]:
        """Get the current adaptive configuration."""
        return {
            'min_rate': self.adaptive_config.min_rate,
            'max_rate': self.adaptive_config.max_rate,
            'increase_factor': self.adaptive_config.increase_factor,
            'decrease_factor': self.adaptive_config.decrease_factor,
            'success_threshold': self.adaptive_config.success_threshold,
            'error_threshold': self.adaptive_config.error_threshold,
            'adjustment_window': self.adaptive_config.adjustment_window
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about rate limiter performance."""
        return {
            'current_rate': self.current_rate,
            'initial_rate': self.initial_rate,
            'total_requests': self.total_requests,
            'successful_requests': self.success_count,
            'rate_limit_errors': self.rate_limit_error_count,
            'total_errors': self.error_count,
            'total_adjustments': len(self.adjustment_history),
            'burst_detection_enabled': self.burst_detection_enabled,
            'last_adjustment_time': self.last_adjustment_time
        }
    
    def enable_burst_detection(self, enabled: bool) -> None:
        """Enable or disable burst detection."""
        self.burst_detection_enabled = enabled
    
    def reset(self) -> None:
        """Reset the rate limiter to initial state."""
        self.last_request_time = None
        self.current_rate = self.initial_rate
        self.success_count = 0
        self.error_count = 0
        self.rate_limit_error_count = 0
        self.total_requests = 0
        self.adjustment_history.clear()
        self.last_adjustment_time = datetime.now()