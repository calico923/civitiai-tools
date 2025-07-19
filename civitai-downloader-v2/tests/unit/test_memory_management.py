#!/usr/bin/env python3
"""
Memory management system tests.
Tests for memory usage calculation, streaming thresholds, and adaptive management.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import importlib.util
from typing import Dict, Any


class TestMemoryManagement:
    """Test memory management system functionality."""
    
    @property
    def memory_dir(self) -> Path:
        """Get the memory management directory."""
        return Path(__file__).parent.parent.parent / "src" / "core" / "memory"
    
    def test_memory_usage_calculation(self):
        """Test accurate memory usage calculation and monitoring."""
        # Import memory manager implementation
        memory_manager_path = self.memory_dir / "memory_manager_impl.py"
        assert memory_manager_path.exists(), "memory_manager_impl.py must exist"
        
        spec = importlib.util.spec_from_file_location("memory_manager_impl", memory_manager_path)
        memory_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory_module)
        
        # Test MemoryManagerImpl class exists
        assert hasattr(memory_module, 'MemoryManagerImpl'), "MemoryManagerImpl class must exist"
        MemoryManagerImpl = memory_module.MemoryManagerImpl
        
        # Create memory manager instance
        memory_manager = MemoryManagerImpl()
        
        # Test memory usage calculation
        memory_usage = memory_manager.get_memory_usage()
        
        # Validate memory usage structure
        assert hasattr(memory_usage, 'current_mb'), "Memory usage must have current_mb"
        assert hasattr(memory_usage, 'peak_mb'), "Memory usage must have peak_mb"
        assert hasattr(memory_usage, 'available_mb'), "Memory usage must have available_mb"
        assert hasattr(memory_usage, 'percentage_used'), "Memory usage must have percentage_used"
        assert hasattr(memory_usage, 'pressure_level'), "Memory usage must have pressure_level"
        
        # Test values are reasonable
        assert memory_usage.current_mb >= 0, "Current memory usage cannot be negative"
        assert memory_usage.peak_mb >= memory_usage.current_mb, "Peak memory should be >= current"
        assert memory_usage.available_mb >= 0, "Available memory cannot be negative"
        assert 0 <= memory_usage.percentage_used <= 100, "Memory percentage must be 0-100"
    
    def test_streaming_threshold_detection(self):
        """Test streaming threshold detection based on expected data size."""
        memory_manager_path = self.memory_dir / "memory_manager_impl.py"
        assert memory_manager_path.exists(), "memory_manager_impl.py must exist"
        
        spec = importlib.util.spec_from_file_location("memory_manager_impl", memory_manager_path)
        memory_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory_module)
        
        MemoryManagerImpl = memory_module.MemoryManagerImpl
        memory_manager = MemoryManagerImpl()
        
        # Test streaming decision for small datasets
        should_stream_small = memory_manager.should_use_streaming(
            expected_count=100,
            estimated_size_mb=50.0
        )
        assert isinstance(should_stream_small, bool), "should_use_streaming must return boolean"
        
        # Test streaming decision for large datasets (10,000+ models)
        should_stream_large = memory_manager.should_use_streaming(
            expected_count=10000,
            estimated_size_mb=2000.0
        )
        assert should_stream_large == True, "Large datasets should trigger streaming"
        
        # Test streaming decision for very large datasets
        should_stream_huge = memory_manager.should_use_streaming(
            expected_count=50000,
            estimated_size_mb=10000.0
        )
        assert should_stream_huge == True, "Huge datasets must trigger streaming"
        
        # Test threshold consistency
        assert memory_manager.should_use_streaming(1000, 600.0) == True, \
            "Should stream when above threshold"
    
    def test_adaptive_threshold_adjustment(self):
        """Test adaptive threshold adjustment based on system conditions."""
        adaptive_thresholds_path = self.memory_dir / "adaptive_thresholds.py"
        assert adaptive_thresholds_path.exists(), "adaptive_thresholds.py must exist"
        
        spec = importlib.util.spec_from_file_location("adaptive_thresholds", adaptive_thresholds_path)
        adaptive_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adaptive_module)
        
        # Test AdaptiveThresholds class exists
        assert hasattr(adaptive_module, 'AdaptiveThresholds'), "AdaptiveThresholds class must exist"
        AdaptiveThresholds = adaptive_module.AdaptiveThresholds
        
        adaptive_thresholds = AdaptiveThresholds()
        
        # Test initial thresholds
        initial_thresholds = adaptive_thresholds.get_current_thresholds()
        assert hasattr(initial_thresholds, 'streaming_threshold_mb'), \
            "Thresholds must have streaming_threshold_mb"
        assert hasattr(initial_thresholds, 'warning_threshold_mb'), \
            "Thresholds must have warning_threshold_mb"
        assert hasattr(initial_thresholds, 'critical_threshold_mb'), \
            "Thresholds must have critical_threshold_mb"
        
        # Test threshold adjustment based on memory pressure
        current_memory_mb = 800.0
        available_memory_mb = 1200.0
        
        adjusted_thresholds = adaptive_thresholds.adjust_thresholds(
            current_memory_mb=current_memory_mb,
            available_memory_mb=available_memory_mb
        )
        
        # Verify thresholds are adjusted appropriately
        assert adjusted_thresholds.streaming_threshold_mb > 0, \
            "Streaming threshold must be positive"
        assert adjusted_thresholds.warning_threshold_mb > adjusted_thresholds.streaming_threshold_mb, \
            "Warning threshold must be higher than streaming threshold"
        assert adjusted_thresholds.critical_threshold_mb > adjusted_thresholds.warning_threshold_mb, \
            "Critical threshold must be highest"
        
        # Test threshold adjustment under high memory pressure
        high_pressure_thresholds = adaptive_thresholds.adjust_thresholds(
            current_memory_mb=1800.0,
            available_memory_mb=200.0
        )
        
        # Under high pressure, thresholds should be more conservative (lower)
        assert high_pressure_thresholds.streaming_threshold_mb <= adjusted_thresholds.streaming_threshold_mb, \
            "High pressure should lower streaming threshold"
    
    def test_memory_optimization_trigger(self):
        """Test memory optimization triggering and execution."""
        memory_manager_path = self.memory_dir / "memory_manager_impl.py"
        spec = importlib.util.spec_from_file_location("memory_manager_impl", memory_manager_path)
        memory_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory_module)
        
        MemoryManagerImpl = memory_module.MemoryManagerImpl
        memory_manager = MemoryManagerImpl()
        
        # Test memory optimization without forcing garbage collection
        optimization_result = memory_manager.optimize_memory(force_gc=False)
        assert isinstance(optimization_result, bool), "optimize_memory must return boolean"
        
        # Test memory optimization with forced garbage collection
        forced_optimization_result = memory_manager.optimize_memory(force_gc=True)
        assert isinstance(forced_optimization_result, bool), \
            "optimize_memory with force_gc must return boolean"
        
        # Test optimal batch size calculation
        optimal_batch = memory_manager.get_optimal_batch_size(
            item_size_mb=2.0,
            total_items=10000
        )
        assert isinstance(optimal_batch, int), "get_optimal_batch_size must return integer"
        assert optimal_batch > 0, "Optimal batch size must be positive"
        assert optimal_batch <= 10000, "Batch size cannot exceed total items"
        
        # Test batch size scales with available memory
        small_batch = memory_manager.get_optimal_batch_size(
            item_size_mb=10.0,  # Larger items
            total_items=1000
        )
        large_batch = memory_manager.get_optimal_batch_size(
            item_size_mb=1.0,   # Smaller items
            total_items=1000
        )
        assert small_batch <= large_batch, \
            "Larger items should result in smaller batch sizes"
    
    def test_memory_statistics_collection(self):
        """Test memory statistics collection and tracking."""
        memory_stats_path = self.memory_dir / "memory_statistics.py"
        assert memory_stats_path.exists(), "memory_statistics.py must exist"
        
        spec = importlib.util.spec_from_file_location("memory_statistics", memory_stats_path)
        stats_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stats_module)
        
        # Test MemoryStatistics class exists
        assert hasattr(stats_module, 'MemoryStatistics'), "MemoryStatistics class must exist"
        MemoryStatistics = stats_module.MemoryStatistics
        
        memory_stats = MemoryStatistics()
        
        # Test statistics recording
        memory_stats.record_memory_event(
            event_type="optimization",
            memory_before_mb=800.0,
            memory_after_mb=600.0,
            context={"operation": "model_processing"}
        )
        
        # Test statistics retrieval
        recent_stats = memory_stats.get_recent_statistics(limit=10)
        assert isinstance(recent_stats, list), "Recent statistics must be a list"
        
        if recent_stats:  # If we have recorded statistics
            stat_entry = recent_stats[0]
            assert 'event_type' in stat_entry, "Statistics must include event_type"
            assert 'memory_before_mb' in stat_entry, "Statistics must include memory_before_mb"
            assert 'memory_after_mb' in stat_entry, "Statistics must include memory_after_mb"
            assert 'timestamp' in stat_entry, "Statistics must include timestamp"
        
        # Test statistics aggregation
        aggregated_stats = memory_stats.get_aggregated_statistics()
        assert isinstance(aggregated_stats, dict), "Aggregated statistics must be a dict"
        
        expected_keys = ['total_events', 'average_memory_usage', 'peak_memory_usage', 'memory_savings']
        for key in expected_keys:
            assert key in aggregated_stats, f"Aggregated stats must include {key}"
    
    def test_memory_pressure_monitoring(self):
        """Test memory pressure level monitoring and callbacks."""
        memory_manager_path = self.memory_dir / "memory_manager_impl.py"
        spec = importlib.util.spec_from_file_location("memory_manager_impl", memory_manager_path)
        memory_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory_module)
        
        MemoryManagerImpl = memory_module.MemoryManagerImpl
        memory_manager = MemoryManagerImpl()
        
        # Test memory pressure monitoring
        pressure_level = memory_manager.monitor_memory_pressure()
        
        # Import MemoryPressure enum from interface
        interface_path = Path(__file__).parent.parent.parent / "src" / "core" / "interfaces" / "memory_manager.py"
        spec = importlib.util.spec_from_file_location("memory_interface", interface_path)
        interface_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(interface_module)
        
        MemoryPressure = interface_module.MemoryPressure
        
        # Validate pressure level - check it's an enum with a valid value
        assert hasattr(pressure_level, 'value'), "Pressure level must be an enum"
        assert pressure_level.value in ['low', 'medium', 'high', 'critical'], \
            f"Pressure level must have valid value, got {pressure_level.value}"
        
        # Test processing recommendation
        recommendation = memory_manager.get_processing_recommendation(
            item_count=5000,
            item_size_mb=1.5
        )
        
        assert hasattr(recommendation, 'mode'), "Recommendation must have processing mode"
        assert hasattr(recommendation, 'batch_size'), "Recommendation must have batch_size"
        assert hasattr(recommendation, 'use_streaming'), "Recommendation must have use_streaming"
        assert hasattr(recommendation, 'estimated_memory_mb'), "Recommendation must have estimated_memory_mb"
        assert hasattr(recommendation, 'confidence_level'), "Recommendation must have confidence_level"
        
        # Validate recommendation values
        assert 0.0 <= recommendation.confidence_level <= 1.0, \
            "Confidence level must be between 0.0 and 1.0"
        assert recommendation.estimated_memory_mb >= 0, \
            "Estimated memory must be non-negative"
    
    def test_memory_safety_checking(self):
        """Test memory safety checking for operations."""
        memory_manager_path = self.memory_dir / "memory_manager_impl.py"
        spec = importlib.util.spec_from_file_location("memory_manager_impl", memory_manager_path)
        memory_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory_module)
        
        MemoryManagerImpl = memory_module.MemoryManagerImpl
        memory_manager = MemoryManagerImpl()
        
        # Test memory safety for small operations
        is_safe_small = memory_manager.check_memory_safety(operation_mb=100.0)
        assert isinstance(is_safe_small, bool), "Memory safety check must return boolean"
        
        # Test memory safety for large operations
        is_safe_large = memory_manager.check_memory_safety(operation_mb=2000.0)
        assert isinstance(is_safe_large, bool), "Memory safety check must return boolean"
        
        # Test processing memory estimation
        estimated_memory = memory_manager.estimate_processing_memory(
            item_count=1000,
            item_size_mb=2.0
        )
        assert isinstance(estimated_memory, float), "Memory estimation must return float"
        assert estimated_memory >= 0, "Estimated memory cannot be negative"
        
        # Verify estimation scales with item count
        estimated_small = memory_manager.estimate_processing_memory(100, 2.0)
        estimated_large = memory_manager.estimate_processing_memory(1000, 2.0)
        assert estimated_large >= estimated_small, \
            "More items should require more memory"
    
    def test_memory_callback_registration(self):
        """Test memory pressure callback registration and triggering."""
        memory_manager_path = self.memory_dir / "memory_manager_impl.py"
        spec = importlib.util.spec_from_file_location("memory_manager_impl", memory_manager_path)
        memory_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory_module)
        
        MemoryManagerImpl = memory_module.MemoryManagerImpl
        memory_manager = MemoryManagerImpl()
        
        # Import MemoryPressure enum
        interface_path = Path(__file__).parent.parent.parent / "src" / "core" / "interfaces" / "memory_manager.py"
        spec = importlib.util.spec_from_file_location("memory_interface", interface_path)
        interface_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(interface_module)
        
        MemoryPressure = interface_module.MemoryPressure
        
        # Test callback registration
        callback_called = []
        
        def test_callback():
            callback_called.append(True)
        
        # This should not raise an exception
        memory_manager.register_memory_callback(
            pressure_level=MemoryPressure.HIGH,
            callback=test_callback
        )
        
        # Test threshold setting
        interface_path = Path(__file__).parent.parent.parent / "src" / "core" / "interfaces" / "memory_manager.py"
        spec = importlib.util.spec_from_file_location("memory_interface", interface_path)
        interface_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(interface_module)
        
        MemoryThresholds = interface_module.MemoryThresholds
        
        new_thresholds = MemoryThresholds(
            streaming_threshold_mb=400.0,
            warning_threshold_mb=800.0,
            critical_threshold_mb=1200.0
        )
        
        # This should not raise an exception
        memory_manager.set_memory_thresholds(new_thresholds)