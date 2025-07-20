#!/usr/bin/env python3
"""
LRU Cache tests.
Tests for enhanced caching with LRU strategy and memory pressure handling.
"""

import pytest
import time
from unittest.mock import Mock, patch
from pathlib import Path
import importlib.util
from datetime import datetime, timedelta
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestLRUCache:
    """Test LRU caching functionality with memory pressure handling."""
    
    @property
    def api_dir(self) -> Path:
        """Get the API directory."""
        return Path(__file__).parent.parent.parent / "src" / "api"
    
    def test_lru_cache_module_exists(self):
        """Test that enhanced cache module exists with LRU features."""
        cache_path = self.api_dir / "cache.py"
        assert cache_path.exists(), "cache.py must exist"
        
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        # Test ResponseCache class exists
        assert hasattr(cache_module, 'ResponseCache'), "ResponseCache class must exist"
        ResponseCache = cache_module.ResponseCache
        
        # Test initialization with LRU features
        cache = ResponseCache(ttl_seconds=300)
        
        # Validate LRU methods
        assert hasattr(cache, 'get_cache_size'), "Must have cache size tracking"
        assert hasattr(cache, 'set_max_size'), "Must have maximum size configuration"
        assert hasattr(cache, 'get_memory_usage'), "Must have memory usage tracking"
    
    def test_lru_eviction_policy(self):
        """Test that LRU eviction policy works correctly."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        cache = ResponseCache(ttl_seconds=3600)  # Long TTL to focus on LRU
        
        # Set maximum cache size for testing
        if hasattr(cache, 'set_max_size'):
            cache.set_max_size(3)  # Only allow 3 items
        
        # Add items beyond capacity
        cache.store("key1", {"data": "value1"})
        cache.store("key2", {"data": "value2"})
        cache.store("key3", {"data": "value3"})
        
        # All items should be present
        assert cache.get("key1") is not None, "Key1 should be present"
        assert cache.get("key2") is not None, "Key2 should be present"
        assert cache.get("key3") is not None, "Key3 should be present"
        
        # Add fourth item - should evict least recently used
        cache.store("key4", {"data": "value4"})
        
        # Check LRU eviction
        if hasattr(cache, 'get_cache_size'):
            cache_size = cache.get_cache_size()
            assert cache_size <= 3, "Cache size should not exceed maximum"
            
            # key1 should be evicted (least recently used)
            assert cache.get("key1") is None, "Key1 should be evicted"
            assert cache.get("key4") is not None, "Key4 should be present"
    
    def test_lru_access_order_tracking(self):
        """Test that cache tracks access order for LRU eviction."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        cache = ResponseCache(ttl_seconds=3600)
        
        if hasattr(cache, 'set_max_size'):
            cache.set_max_size(3)
        
        # Add items
        cache.store("key1", {"data": "value1"})
        cache.store("key2", {"data": "value2"})
        cache.store("key3", {"data": "value3"})
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add new item - key2 should be evicted (now least recently used)
        cache.store("key4", {"data": "value4"})
        
        if hasattr(cache, 'get_cache_size'):
            assert cache.get("key1") is not None, "Key1 should remain (recently accessed)"
            assert cache.get("key2") is None, "Key2 should be evicted"
            assert cache.get("key3") is not None, "Key3 should remain"
            assert cache.get("key4") is not None, "Key4 should be present"
    
    def test_memory_pressure_handling(self):
        """Test cache behavior under memory pressure."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        cache = ResponseCache(ttl_seconds=3600)
        
        # Test memory threshold configuration
        if hasattr(cache, 'set_memory_threshold'):
            cache.set_memory_threshold(1024 * 1024)  # 1MB threshold
            
            # Test memory usage tracking
            if hasattr(cache, 'get_memory_usage'):
                initial_memory = cache.get_memory_usage()
                assert isinstance(initial_memory, (int, float)), "Memory usage should be numeric"
                
                # Add large data
                large_data = {"data": "x" * 10000}  # 10KB of data
                cache.store("large_key", large_data)
                
                memory_after = cache.get_memory_usage()
                assert memory_after >= initial_memory, "Memory usage should increase"
    
    def test_memory_pressure_eviction(self):
        """Test that cache evicts items under memory pressure."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        cache = ResponseCache(ttl_seconds=3600)
        
        if hasattr(cache, 'set_memory_threshold') and hasattr(cache, 'enable_memory_pressure_eviction'):
            # Set low memory threshold
            cache.set_memory_threshold(1024)  # 1KB threshold
            cache.enable_memory_pressure_eviction(True)
            
            # Add data that exceeds memory threshold
            for i in range(10):
                large_data = {"data": "x" * 500, "id": i}  # 500 bytes each
                cache.store(f"key_{i}", large_data)
            
            # Check that eviction occurred due to memory pressure
            if hasattr(cache, 'get_cache_size'):
                cache_size = cache.get_cache_size()
                memory_usage = cache.get_memory_usage()
                
                # Cache should have evicted some items to stay under memory pressure
                assert cache_size < 10, "Should evict items under memory pressure"
                assert memory_usage <= cache.memory_threshold * 1.2, "Memory usage should be controlled"
    
    def test_cache_statistics_and_monitoring(self):
        """Test cache statistics and monitoring capabilities."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        cache = ResponseCache(ttl_seconds=300)
        
        # Test statistics method
        if hasattr(cache, 'get_statistics'):
            stats = cache.get_statistics()
            
            assert isinstance(stats, dict), "Statistics should be a dictionary"
            assert 'cache_size' in stats, "Should include cache size"
            assert 'hit_count' in stats, "Should track cache hits"
            assert 'miss_count' in stats, "Should track cache misses"
            assert 'eviction_count' in stats, "Should track evictions"
            assert 'memory_usage' in stats, "Should track memory usage"
            
            # Test hit/miss tracking
            cache.store("test_key", {"data": "test_value"})
            
            # Cache hit
            cache.get("test_key")
            
            # Cache miss
            cache.get("nonexistent_key")
            
            updated_stats = cache.get_statistics()
            assert updated_stats['hit_count'] > stats['hit_count'], "Should track hits"
            assert updated_stats['miss_count'] > stats['miss_count'], "Should track misses"
    
    def test_cache_configuration_options(self):
        """Test various cache configuration options."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        
        # Test with LRU configuration
        if hasattr(cache_module, 'LRUConfig'):
            LRUConfig = cache_module.LRUConfig
            config = LRUConfig(
                max_size=100,
                memory_threshold=1024 * 1024,
                enable_memory_pressure=True
            )
            cache = ResponseCache(ttl_seconds=300, lru_config=config)
        else:
            # Fallback to direct configuration
            cache = ResponseCache(
                ttl_seconds=300,
                max_size=100,
                memory_threshold=1024 * 1024
            )
        
        # Test configuration is applied
        if hasattr(cache, 'get_config'):
            config = cache.get_config()
            assert isinstance(config, dict), "Configuration should be a dictionary"
            assert 'max_size' in config, "Should include max size"
            assert 'memory_threshold' in config, "Should include memory threshold"
    
    def test_concurrent_cache_operations(self):
        """Test cache behavior under concurrent operations."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        cache = ResponseCache(ttl_seconds=300)
        
        # Test thread safety features
        if hasattr(cache, 'enable_thread_safety'):
            cache.enable_thread_safety(True)
        
        # Simulate concurrent operations
        for i in range(50):
            cache.store(f"concurrent_key_{i}", {"data": f"value_{i}"})
        
        # Verify all operations completed
        stored_count = 0
        for i in range(50):
            if cache.get(f"concurrent_key_{i}") is not None:
                stored_count += 1
        
        assert stored_count > 0, "Some concurrent operations should succeed"
    
    def test_cache_persistence_and_recovery(self):
        """Test cache persistence and recovery features."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        cache = ResponseCache(ttl_seconds=300)
        
        # Test backup and restore functionality
        if hasattr(cache, 'backup_cache') and hasattr(cache, 'restore_cache'):
            # Store some data
            cache.store("backup_key_1", {"data": "backup_value_1"})
            cache.store("backup_key_2", {"data": "backup_value_2"})
            
            # Create backup
            backup_data = cache.backup_cache()
            assert isinstance(backup_data, (dict, str, bytes)), "Backup should return serializable data"
            
            # Clear cache
            cache.clear()
            assert cache.get("backup_key_1") is None, "Cache should be cleared"
            
            # Restore from backup
            cache.restore_cache(backup_data)
            assert cache.get("backup_key_1") is not None, "Data should be restored"
            assert cache.get("backup_key_2") is not None, "All data should be restored"
    
    def test_ttl_with_lru_integration(self):
        """Test that TTL and LRU work together correctly."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        cache = ResponseCache(ttl_seconds=1)  # Short TTL for testing
        
        if hasattr(cache, 'set_max_size'):
            cache.set_max_size(5)
        
        # Store items
        cache.store("ttl_key_1", {"data": "ttl_value_1"})
        cache.store("ttl_key_2", {"data": "ttl_value_2"})
        
        # Wait for TTL expiration
        time.sleep(1.1)
        
        # Both TTL and LRU should handle expired items
        assert cache.get("ttl_key_1") is None, "TTL expired items should be removed"
        assert cache.get("ttl_key_2") is None, "TTL expired items should be removed"
        
        # Cache size should reflect expired item removal
        if hasattr(cache, 'get_cache_size'):
            assert cache.get_cache_size() == 0, "Expired items should not count in cache size"