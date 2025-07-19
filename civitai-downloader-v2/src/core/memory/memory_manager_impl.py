"""
MemoryManagerImpl - Concrete implementation of memory management.

This module provides the concrete implementation of the MemoryManager interface
for handling large datasets efficiently, especially for 10,000+ model processing.
"""

import gc
import psutil
import os
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

import sys
from pathlib import Path

# Add the src directory to the path for importing
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from core.interfaces.memory_manager import (
    MemoryManager, MemoryUsage, MemoryPressure, ProcessingMode,
    MemoryThresholds, ProcessingRecommendation
)


class MemoryManagerImpl(MemoryManager):
    """
    Concrete implementation of memory management for large dataset processing.
    
    This implementation provides memory monitoring, threshold management,
    and optimization strategies to handle 10,000+ model processing efficiently.
    """
    
    def __init__(self, thresholds: Optional[MemoryThresholds] = None):
        """
        Initialize memory manager with configurable thresholds.
        
        Args:
            thresholds: Custom memory thresholds, uses defaults if None
        """
        self._thresholds = thresholds or MemoryThresholds()
        self._callbacks: Dict[MemoryPressure, List[Callable[[], None]]] = {
            pressure: [] for pressure in MemoryPressure
        }
        self._last_pressure_level = MemoryPressure.LOW
        
        # Get system memory info once at initialization
        self._system_memory = psutil.virtual_memory()
        self._total_memory_mb = self._system_memory.total / (1024 * 1024)
    
    def should_use_streaming(self, expected_count: int, estimated_size_mb: Optional[float] = None) -> bool:
        """
        Determine if streaming processing should be used based on expected data size.
        
        Args:
            expected_count: Expected number of items to process
            estimated_size_mb: Estimated memory usage in MB (optional)
            
        Returns:
            True if streaming processing is recommended
        """
        # If estimated size is provided, use it directly
        if estimated_size_mb is not None:
            return estimated_size_mb > self._thresholds.streaming_threshold_mb
        
        # Estimate memory based on item count (rough approximation)
        # Assume average 0.5MB per model metadata + processing overhead
        estimated_mb = expected_count * 0.5 * 1.5  # 50% overhead factor
        
        # Always stream for large datasets (10,000+ items)
        if expected_count >= 10000:
            return True
        
        # Use threshold-based decision for smaller datasets
        return estimated_mb > self._thresholds.streaming_threshold_mb
    
    def get_memory_usage(self) -> MemoryUsage:
        """
        Get current memory usage statistics.
        
        Returns:
            MemoryUsage object with current memory statistics
        """
        try:
            # Get current process memory info
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            # Get system memory info
            system_memory = psutil.virtual_memory()
            
            current_mb = memory_info.rss / (1024 * 1024)
            available_mb = system_memory.available / (1024 * 1024)
            percentage_used = (memory_info.rss / system_memory.total) * 100
            
            # Calculate peak memory (use high water mark if available)
            try:
                peak_mb = process.memory_info().peak_wset / (1024 * 1024)
            except AttributeError:
                # peak_wset not available on this platform, use current as approximation
                peak_mb = current_mb
            
            # Determine pressure level
            pressure_level = self._calculate_pressure_level(current_mb, available_mb)
            
            return MemoryUsage(
                current_mb=current_mb,
                peak_mb=peak_mb,
                available_mb=available_mb,
                percentage_used=percentage_used,
                pressure_level=pressure_level
            )
        except Exception as e:
            # Fallback to minimal memory info
            return MemoryUsage(
                current_mb=100.0,  # Conservative estimate
                peak_mb=100.0,
                available_mb=1000.0,
                percentage_used=10.0,
                pressure_level=MemoryPressure.LOW
            )
    
    def optimize_memory(self, force_gc: bool = False) -> bool:
        """
        Optimize memory usage by cleaning up unused objects.
        
        Args:
            force_gc: Force garbage collection
            
        Returns:
            True if optimization was successful
        """
        try:
            memory_before = self.get_memory_usage().current_mb
            
            if force_gc:
                # Force full garbage collection
                gc.collect()
                gc.collect()  # Run twice for thoroughness
                gc.collect()
            else:
                # Gentle optimization
                gc.collect()
            
            memory_after = self.get_memory_usage().current_mb
            
            # Consider optimization successful if we freed some memory
            return memory_after <= memory_before
        except Exception:
            return False
    
    def get_optimal_batch_size(self, item_size_mb: float, total_items: int) -> int:
        """
        Calculate optimal batch size based on available memory.
        
        Args:
            item_size_mb: Estimated size per item in MB
            total_items: Total number of items to process
            
        Returns:
            Optimal batch size for processing
        """
        memory_usage = self.get_memory_usage()
        
        # Calculate available memory for batch processing
        # Use 70% of available memory to leave buffer
        usable_memory_mb = memory_usage.available_mb * 0.7
        
        # Calculate items that fit in available memory
        items_per_memory = int(usable_memory_mb / item_size_mb) if item_size_mb > 0 else total_items
        
        # Apply min/max constraints
        optimal_batch = max(
            self._thresholds.min_batch_size,
            min(items_per_memory, self._thresholds.max_batch_size, total_items)
        )
        
        return optimal_batch
    
    def monitor_memory_pressure(self) -> MemoryPressure:
        """
        Monitor current memory pressure level.
        
        Returns:
            Current memory pressure level
        """
        memory_usage = self.get_memory_usage()
        pressure_level = memory_usage.pressure_level
        
        # Trigger callbacks if pressure level changed
        if pressure_level != self._last_pressure_level:
            self._trigger_pressure_callbacks(pressure_level)
            self._last_pressure_level = pressure_level
        
        return pressure_level
    
    def estimate_processing_memory(self, item_count: int, item_size_mb: float) -> float:
        """
        Estimate memory requirements for processing operation.
        
        Args:
            item_count: Number of items to process
            item_size_mb: Estimated size per item in MB
            
        Returns:
            Estimated total memory requirement in MB
        """
        # Base memory for items
        base_memory = item_count * item_size_mb
        
        # Add processing overhead (typically 30-50% for data structures, etc.)
        processing_overhead = base_memory * 0.4
        
        # Add system buffer (10% of total)
        system_buffer = base_memory * 0.1
        
        return base_memory + processing_overhead + system_buffer
    
    def get_processing_recommendation(self, 
                                    item_count: int, 
                                    item_size_mb: float) -> ProcessingRecommendation:
        """
        Get processing mode recommendation based on memory analysis.
        
        Args:
            item_count: Number of items to process
            item_size_mb: Estimated size per item in MB
            
        Returns:
            ProcessingRecommendation with suggested approach
        """
        estimated_memory = self.estimate_processing_memory(item_count, item_size_mb)
        memory_usage = self.get_memory_usage()
        
        # Determine processing mode
        if estimated_memory > self._thresholds.critical_threshold_mb:
            mode = ProcessingMode.STREAMING
            use_streaming = True
            batch_size = None
            confidence = 0.95
        elif estimated_memory > self._thresholds.warning_threshold_mb:
            mode = ProcessingMode.BATCH
            use_streaming = True
            batch_size = self.get_optimal_batch_size(item_size_mb, item_count)
            confidence = 0.85
        elif memory_usage.available_mb < estimated_memory:
            mode = ProcessingMode.BATCH
            use_streaming = False
            batch_size = self.get_optimal_batch_size(item_size_mb, item_count)
            confidence = 0.75
        else:
            mode = ProcessingMode.BATCH
            use_streaming = False
            batch_size = min(item_count, self._thresholds.max_batch_size)
            confidence = 0.90
        
        return ProcessingRecommendation(
            mode=mode,
            batch_size=batch_size,
            use_streaming=use_streaming,
            estimated_memory_mb=estimated_memory,
            confidence_level=confidence
        )
    
    def set_memory_thresholds(self, thresholds: MemoryThresholds) -> None:
        """
        Update memory threshold configuration.
        
        Args:
            thresholds: New memory threshold settings
            
        Raises:
            ValidationError: If thresholds are invalid
        """
        # Validate thresholds
        if thresholds.streaming_threshold_mb <= 0:
            raise ValueError("Streaming threshold must be positive")
        if thresholds.warning_threshold_mb <= thresholds.streaming_threshold_mb:
            raise ValueError("Warning threshold must be higher than streaming threshold")
        if thresholds.critical_threshold_mb <= thresholds.warning_threshold_mb:
            raise ValueError("Critical threshold must be higher than warning threshold")
        if thresholds.min_batch_size <= 0:
            raise ValueError("Minimum batch size must be positive")
        if thresholds.max_batch_size <= thresholds.min_batch_size:
            raise ValueError("Maximum batch size must be higher than minimum")
        
        self._thresholds = thresholds
    
    def register_memory_callback(self, 
                                pressure_level: MemoryPressure, 
                                callback: Callable[[], None]) -> None:
        """
        Register callback for memory pressure events.
        
        Args:
            pressure_level: Memory pressure level to monitor
            callback: Function to call when pressure level is reached
        """
        if pressure_level not in self._callbacks:
            self._callbacks[pressure_level] = []
        
        self._callbacks[pressure_level].append(callback)
    
    def _calculate_pressure_level(self, current_mb: float, available_mb: float) -> MemoryPressure:
        """
        Calculate memory pressure level based on current usage.
        
        Args:
            current_mb: Current memory usage in MB
            available_mb: Available memory in MB
            
        Returns:
            Calculated memory pressure level
        """
        if current_mb > self._thresholds.critical_threshold_mb or available_mb < 100:
            return MemoryPressure.CRITICAL
        elif current_mb > self._thresholds.warning_threshold_mb or available_mb < 500:
            return MemoryPressure.HIGH
        elif current_mb > self._thresholds.streaming_threshold_mb or available_mb < 1000:
            return MemoryPressure.MEDIUM
        else:
            return MemoryPressure.LOW
    
    def _trigger_pressure_callbacks(self, pressure_level: MemoryPressure) -> None:
        """
        Trigger callbacks for the given pressure level.
        
        Args:
            pressure_level: Memory pressure level that was reached
        """
        callbacks = self._callbacks.get(pressure_level, [])
        for callback in callbacks:
            try:
                callback()
            except Exception:
                # Don't let callback errors break memory monitoring
                pass