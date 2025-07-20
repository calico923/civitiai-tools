#!/usr/bin/env python3
"""
Response Cache for CivitAI API requests.
Implements TTL-based caching with LRU eviction and memory pressure handling.
"""

import hashlib
import json
import sys
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class LRUConfig:
    """Configuration for LRU cache behavior."""
    max_size: int = 1000
    memory_threshold: int = 100 * 1024 * 1024  # 100MB default
    enable_memory_pressure: bool = True
    enable_thread_safety: bool = False


class ResponseCache:
    """TTL-based response cache with LRU eviction and memory pressure handling."""
    
    def __init__(self, ttl_seconds: int = 300, 
                 lru_config: Optional[LRUConfig] = None,
                 max_size: Optional[int] = None,
                 memory_threshold: Optional[int] = None):
        """
        Initialize response cache.
        
        Args:
            ttl_seconds: Time to live for cached responses in seconds
            lru_config: LRU configuration object
            max_size: Maximum cache size (fallback if no lru_config)
            memory_threshold: Memory threshold in bytes (fallback if no lru_config)
        """
        self.ttl_seconds = ttl_seconds
        
        # Configure LRU behavior
        if lru_config:
            self.lru_config = lru_config
        else:
            self.lru_config = LRUConfig(
                max_size=max_size or 1000,
                memory_threshold=memory_threshold or 100 * 1024 * 1024
            )
        
        # Use OrderedDict for LRU tracking
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Statistics tracking
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        self.memory_pressure_evictions = 0
        
        # Thread safety
        self.lock = threading.RLock() if self.lru_config.enable_thread_safety else None
    
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
        Store data in cache with timestamp and LRU tracking.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        def _store():
            # Update existing entry or add new one
            self.cache[cache_key] = {
                'data': data,
                'timestamp': datetime.now(),
                'access_count': 1,
                'size': self._estimate_size(data)
            }
            
            # Move to end (most recently used)
            self.cache.move_to_end(cache_key)
            
            # Check for eviction needs
            self._check_eviction_needs()
        
        if self.lock:
            with self.lock:
                _store()
        else:
            _store()
    
    def get(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve data from cache if not expired, with LRU tracking.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data or None if expired/not found
        """
        def _get():
            if cache_key not in self.cache:
                self.miss_count += 1
                return None
            
            cache_entry = self.cache[cache_key]
            expiry_time = cache_entry['timestamp'] + timedelta(seconds=self.ttl_seconds)
            
            if datetime.now() > expiry_time:
                # Cache expired, remove entry
                del self.cache[cache_key]
                self.miss_count += 1
                return None
            
            # Update access tracking and move to end (most recently used)
            cache_entry['access_count'] += 1
            self.cache.move_to_end(cache_key)
            self.hit_count += 1
            
            return cache_entry['data']
        
        if self.lock:
            with self.lock:
                return _get()
        else:
            return _get()
    
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
        def _cleanup():
            current_time = datetime.now()
            expired_keys = []
            
            for key, entry in self.cache.items():
                expiry_time = entry['timestamp'] + timedelta(seconds=self.ttl_seconds)
                if current_time > expiry_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)
        
        if self.lock:
            with self.lock:
                return _cleanup()
        else:
            return _cleanup()
    
    def get_cache_size(self) -> int:
        """Get current number of items in cache."""
        return len(self.cache)
    
    def set_max_size(self, max_size: int) -> None:
        """Set maximum cache size."""
        self.lru_config.max_size = max_size
        self._check_eviction_needs()
    
    def get_memory_usage(self) -> int:
        """
        Get approximate memory usage of cache in bytes.
        
        Returns:
            Estimated memory usage in bytes
        """
        total_size = 0
        for entry in self.cache.values():
            total_size += entry.get('size', 0)
        
        # Add overhead for OrderedDict structure
        total_size += len(self.cache) * 200  # Approximate overhead per entry
        
        return total_size
    
    def set_memory_threshold(self, threshold_bytes: int) -> None:
        """Set memory threshold for pressure handling."""
        self.lru_config.memory_threshold = threshold_bytes
        self.memory_threshold = threshold_bytes
    
    def enable_memory_pressure_eviction(self, enabled: bool) -> None:
        """Enable or disable memory pressure eviction."""
        self.lru_config.enable_memory_pressure = enabled
    
    def enable_thread_safety(self, enabled: bool) -> None:
        """Enable or disable thread safety."""
        if enabled and not self.lock:
            self.lock = threading.RLock()
        elif not enabled:
            self.lock = None
        self.lru_config.enable_thread_safety = enabled
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate the size of data in bytes."""
        try:
            if isinstance(data, (str, bytes)):
                return len(data)
            elif isinstance(data, (int, float)):
                return sys.getsizeof(data)
            elif isinstance(data, (list, tuple)):
                return sum(self._estimate_size(item) for item in data)
            elif isinstance(data, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in data.items())
            else:
                return sys.getsizeof(data)
        except:
            # Fallback estimation
            return 1000
    
    def _check_eviction_needs(self) -> None:
        """Check if eviction is needed due to size or memory pressure."""
        # Size-based eviction
        while len(self.cache) > self.lru_config.max_size:
            self._evict_lru()
        
        # Memory pressure eviction
        if self.lru_config.enable_memory_pressure:
            while self.get_memory_usage() > self.lru_config.memory_threshold:
                if not self.cache:  # Prevent infinite loop
                    break
                self._evict_lru(memory_pressure=True)
    
    def _evict_lru(self, memory_pressure: bool = False) -> None:
        """Evict the least recently used item."""
        if self.cache:
            # Remove from beginning (least recently used)
            self.cache.popitem(last=False)
            self.eviction_count += 1
            if memory_pressure:
                self.memory_pressure_evictions += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            'cache_size': len(self.cache),
            'max_size': self.lru_config.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': self.hit_count / max(1, self.hit_count + self.miss_count),
            'eviction_count': self.eviction_count,
            'memory_pressure_evictions': self.memory_pressure_evictions,
            'memory_usage': self.get_memory_usage(),
            'memory_threshold': self.lru_config.memory_threshold,
            'ttl_seconds': self.ttl_seconds
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get current cache configuration."""
        return {
            'max_size': self.lru_config.max_size,
            'memory_threshold': self.lru_config.memory_threshold,
            'enable_memory_pressure': self.lru_config.enable_memory_pressure,
            'enable_thread_safety': self.lru_config.enable_thread_safety,
            'ttl_seconds': self.ttl_seconds
        }
    
    def backup_cache(self) -> Dict[str, Any]:
        """Create a backup of cache data."""
        backup_data = {}
        for key, entry in self.cache.items():
            backup_data[key] = {
                'data': entry['data'],
                'timestamp': entry['timestamp'].isoformat(),
                'access_count': entry['access_count']
            }
        return backup_data
    
    def restore_cache(self, backup_data: Dict[str, Any]) -> None:
        """Restore cache from backup data."""
        def _restore():
            self.cache.clear()
            for key, entry in backup_data.items():
                try:
                    self.cache[key] = {
                        'data': entry['data'],
                        'timestamp': datetime.fromisoformat(entry['timestamp']),
                        'access_count': entry.get('access_count', 1),
                        'size': self._estimate_size(entry['data'])
                    }
                except Exception:
                    continue  # Skip corrupted entries
            
            self._check_eviction_needs()
        
        if self.lock:
            with self.lock:
                _restore()
        else:
            _restore()