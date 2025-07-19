#!/usr/bin/env python3
"""
Response Cache for CivitAI API requests.
Implements TTL-based caching to reduce API calls and improve performance.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class ResponseCache:
    """TTL-based response cache for API calls."""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize response cache.
        
        Args:
            ttl_seconds: Time to live for cached responses in seconds
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """
        Generate a cache key for endpoint and parameters.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Cache key string
        """
        # Sort parameters for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True)
        cache_data = f"{endpoint}:{sorted_params}"
        
        # Use hash for shorter keys
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def store(self, cache_key: str, data: Any) -> None:
        """
        Store data in cache with timestamp.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def get(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve data from cache if not expired.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data or None if expired/not found
        """
        if cache_key not in self.cache:
            return None
        
        cache_entry = self.cache[cache_key]
        expiry_time = cache_entry['timestamp'] + timedelta(seconds=self.ttl_seconds)
        
        if datetime.now() > expiry_time:
            # Cache expired, remove entry
            del self.cache[cache_key]
            return None
        
        return cache_entry['data']
    
    def is_cache_hit(self, cache_key: str) -> bool:
        """
        Check if cache key exists and is not expired.
        
        Args:
            cache_key: Cache key
            
        Returns:
            True if cache hit, False otherwise
        """
        return self.get(cache_key) is not None
    
    def clear(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        current_time = datetime.now()
        expired_keys = []
        
        for key, entry in self.cache.items():
            expiry_time = entry['timestamp'] + timedelta(seconds=self.ttl_seconds)
            if current_time > expiry_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)