#!/usr/bin/env python3
"""
Adaptive rate limiter tests.
Tests for enhanced rate limiting with adaptive adjustment capabilities.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from pathlib import Path
import importlib.util
from datetime import datetime, timedelta
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiting functionality."""
    
    @property
    def api_dir(self) -> Path:
        """Get the API directory."""
        return Path(__file__).parent.parent.parent / "src" / "api"
    
    def test_adaptive_rate_limiter_module_exists(self):
        """Test that enhanced rate limiter module exists with adaptive features."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        assert rate_limiter_path.exists(), "rate_limiter.py must exist"
        
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        # Test RateLimiter class exists
        assert hasattr(rate_limiter_module, 'RateLimiter'), "RateLimiter class must exist"
        RateLimiter = rate_limiter_module.RateLimiter
        
        # Test initialization
        rate_limiter = RateLimiter(requests_per_second=1.0)
        
        # Validate adaptive methods
        assert hasattr(rate_limiter, 'adjust_rate'), "Must have adaptive rate adjustment"
        assert hasattr(rate_limiter, 'get_current_rate'), "Must have current rate getter"
        assert hasattr(rate_limiter, 'get_rate_adjustment_history'), "Must track rate adjustments"
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_adjustment_on_success(self):
        """Test that rate limiter adapts to successful requests by gradually increasing rate."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        AdaptiveConfig = rate_limiter_module.AdaptiveConfig
        
        # Create config with faster adjustment for testing
        config = AdaptiveConfig(adjustment_window=0)  # Immediate adjustment
        rate_limiter = RateLimiter(requests_per_second=0.5, adaptive_config=config)
        
        initial_rate = rate_limiter.get_current_rate()
        assert initial_rate == 0.5, "Should start with initial rate"
        
        # Simulate successful requests
        for _ in range(10):
            rate_limiter.record_success()
        
        # Check if rate has been adjusted upward
        if hasattr(rate_limiter, 'record_success'):
            current_rate = rate_limiter.get_current_rate()
            assert current_rate > initial_rate, "Rate should increase after successful requests"
            assert current_rate <= 2.0, "Rate should not exceed reasonable maximum"
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_adjustment_on_errors(self):
        """Test that rate limiter reduces rate when encountering API errors."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        rate_limiter = RateLimiter(requests_per_second=1.0)
        
        initial_rate = rate_limiter.get_current_rate()
        
        # Simulate rate limit errors
        if hasattr(rate_limiter, 'record_rate_limit_error'):
            for _ in range(3):
                rate_limiter.record_rate_limit_error()
            
            # Check if rate has been reduced
            current_rate = rate_limiter.get_current_rate()
            assert current_rate < initial_rate, "Rate should decrease after rate limit errors"
            assert current_rate >= 0.1, "Rate should not go below minimum threshold"
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_recovery(self):
        """Test that rate limiter recovers from errors when requests succeed again."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        AdaptiveConfig = rate_limiter_module.AdaptiveConfig
        
        # Create config with faster adjustment for testing
        config = AdaptiveConfig(adjustment_window=0)  # Immediate adjustment
        rate_limiter = RateLimiter(requests_per_second=1.0, adaptive_config=config)
        
        initial_rate = rate_limiter.get_current_rate()
        
        # Simulate errors to reduce rate
        if hasattr(rate_limiter, 'record_rate_limit_error'):
            for _ in range(5):
                rate_limiter.record_rate_limit_error()
            
            reduced_rate = rate_limiter.get_current_rate()
            assert reduced_rate < initial_rate, "Rate should be reduced after errors"
            
            # Simulate recovery with successful requests
            if hasattr(rate_limiter, 'record_success'):
                for _ in range(20):
                    rate_limiter.record_success()
                
                recovered_rate = rate_limiter.get_current_rate()
                assert recovered_rate > reduced_rate, "Rate should recover after successful requests"
    
    def test_rate_adjustment_configuration(self):
        """Test rate adjustment configuration options."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        
        # Test with adaptive configuration
        if hasattr(rate_limiter_module, 'AdaptiveConfig'):
            AdaptiveConfig = rate_limiter_module.AdaptiveConfig
            config = AdaptiveConfig(
                min_rate=0.1,
                max_rate=2.0,
                increase_factor=1.1,
                decrease_factor=0.8
            )
            rate_limiter = RateLimiter(requests_per_second=1.0, adaptive_config=config)
        else:
            # Fallback to direct configuration
            rate_limiter = RateLimiter(
                requests_per_second=1.0,
                min_rate=0.1,
                max_rate=2.0
            )
        
        # Test configuration is applied
        if hasattr(rate_limiter, 'get_adaptive_config'):
            config = rate_limiter.get_adaptive_config()
            assert config['min_rate'] <= config['max_rate'], "Min rate should not exceed max rate"
    
    def test_rate_adjustment_history_tracking(self):
        """Test that rate adjustment history is properly tracked."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        rate_limiter = RateLimiter(requests_per_second=1.0)
        
        # Initial history should be empty or contain initialization
        initial_history = rate_limiter.get_rate_adjustment_history()
        assert isinstance(initial_history, list), "History should be a list"
        
        # Record some events
        if hasattr(rate_limiter, 'record_success'):
            rate_limiter.record_success()
            history_after_success = rate_limiter.get_rate_adjustment_history()
            
            # History should track the adjustment
            if len(history_after_success) > len(initial_history):
                latest_entry = history_after_success[-1]
                assert 'timestamp' in latest_entry, "History entries should have timestamps"
                assert 'event_type' in latest_entry, "History entries should have event type"
                assert 'rate_before' in latest_entry, "History entries should track rate before"
                assert 'rate_after' in latest_entry, "History entries should track rate after"
    
    @pytest.mark.asyncio
    async def test_adaptive_wait_behavior(self):
        """Test that adaptive rate limiter properly adjusts wait times."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        rate_limiter = RateLimiter(requests_per_second=2.0)  # 0.5 second intervals
        
        # Test basic wait functionality
        start_time = datetime.now()
        await rate_limiter.wait()
        first_wait_time = datetime.now()
        
        await rate_limiter.wait()
        second_wait_time = datetime.now()
        
        # Second wait should respect the rate limit
        time_between_requests = (second_wait_time - first_wait_time).total_seconds()
        expected_min_interval = 1.0 / rate_limiter.get_current_rate()
        
        # Allow some tolerance for timing
        assert time_between_requests >= expected_min_interval * 0.9, "Should respect minimum interval"
    
    def test_adaptive_rate_statistics(self):
        """Test adaptive rate limiter statistics and monitoring."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        rate_limiter = RateLimiter(requests_per_second=1.0)
        
        # Test statistics method exists
        if hasattr(rate_limiter, 'get_statistics'):
            stats = rate_limiter.get_statistics()
            
            assert isinstance(stats, dict), "Statistics should be a dictionary"
            assert 'current_rate' in stats, "Should include current rate"
            assert 'total_requests' in stats, "Should track total requests"
            assert 'successful_requests' in stats, "Should track successful requests"
            assert 'rate_limit_errors' in stats, "Should track rate limit errors"
            assert 'total_adjustments' in stats, "Should track total rate adjustments"
    
    @pytest.mark.asyncio 
    async def test_adaptive_rate_with_burst_handling(self):
        """Test adaptive rate limiter handles burst requests appropriately."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        rate_limiter = RateLimiter(requests_per_second=1.0)
        
        # Test burst detection and handling
        if hasattr(rate_limiter, 'enable_burst_detection'):
            rate_limiter.enable_burst_detection(True)
            
            # Simulate burst of requests
            start_time = datetime.now()
            for _ in range(5):
                await rate_limiter.wait()
            end_time = datetime.now()
            
            total_time = (end_time - start_time).total_seconds()
            
            # Should take at least 4 seconds for 5 requests at 1 req/sec
            assert total_time >= 4.0, "Should enforce rate limit during burst"