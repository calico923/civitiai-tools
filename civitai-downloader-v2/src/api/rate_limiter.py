#!/usr/bin/env python3
"""
Rate Limiter for CivitAI API requests.
Implements rate limiting to respect API usage policies.
"""

import asyncio
from datetime import datetime
from typing import Optional


class RateLimiter:
    """Rate limiter to control API request frequency."""
    
    def __init__(self, requests_per_second: float = 0.5):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum requests per second allowed
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0
        self.last_request_time: Optional[datetime] = None
    
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
        
        if time_since_last < self.min_interval:
            # Need to wait
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = datetime.now()
    
    def reset(self) -> None:
        """Reset the rate limiter."""
        self.last_request_time = None