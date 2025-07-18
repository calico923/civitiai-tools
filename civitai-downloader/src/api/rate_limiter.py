"""Rate limiting functionality for API calls."""

import time


class RateLimiter:
    """Manages API call rate limiting to respect service limits."""
    
    def __init__(self, calls_per_second: float = 0.5):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum calls per second (default: 0.5 = one call every 2 seconds)
        """
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
        self.calls_made = 0
        self.start_time = time.time()
    
    def wait_if_needed(self, verbose: bool = True) -> None:
        """
        Wait if necessary to respect rate limits.
        
        Args:
            verbose: Whether to print wait messages
        """
        current_time = time.time()
        elapsed = current_time - self.last_call
        
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            if verbose:
                print(f"Rate limiting: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        self.last_call = time.time()
        self.calls_made += 1
    
    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with rate limiter stats
        """
        elapsed_time = time.time() - self.start_time
        avg_rate = self.calls_made / elapsed_time if elapsed_time > 0 else 0
        
        return {
            "calls_made": self.calls_made,
            "elapsed_time": elapsed_time,
            "average_rate": avg_rate,
            "configured_rate": 1.0 / self.min_interval
        }
    
    def reset(self) -> None:
        """Reset rate limiter statistics."""
        self.last_call = 0.0
        self.calls_made = 0
        self.start_time = time.time()