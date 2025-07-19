"""
MemoryManager - Abstract interface for memory management implementations.

This module defines the abstract base class for implementing memory management
strategies to handle large datasets efficiently, especially for 10,000+ model processing.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum


class MemoryPressure(Enum):
    """Memory pressure levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProcessingMode(Enum):
    """Processing mode based on memory availability."""
    BATCH = "batch"           # Process in batches
    STREAMING = "streaming"   # Stream processing
    SINGLE = "single"         # Process one at a time


@dataclass
class MemoryUsage:
    """Memory usage statistics."""
    current_mb: float
    peak_mb: float
    available_mb: float
    percentage_used: float
    pressure_level: MemoryPressure


@dataclass
class MemoryThresholds:
    """Memory threshold configuration."""
    streaming_threshold_mb: float = 500.0
    warning_threshold_mb: float = 1000.0
    critical_threshold_mb: float = 1500.0
    max_batch_size: int = 1000
    min_batch_size: int = 10


@dataclass
class ProcessingRecommendation:
    """Memory-based processing recommendation."""
    mode: ProcessingMode
    batch_size: Optional[int]
    use_streaming: bool
    estimated_memory_mb: float
    confidence_level: float


class MemoryManager(ABC):
    """
    Abstract base class for memory management implementations.
    
    This interface defines the contract for implementing memory management
    strategies to efficiently handle large datasets and prevent memory issues
    during model processing operations.
    """
    
    @abstractmethod
    def should_use_streaming(self, expected_count: int, estimated_size_mb: Optional[float] = None) -> bool:
        """
        Determine if streaming processing should be used based on expected data size.
        
        Args:
            expected_count: Expected number of items to process
            estimated_size_mb: Estimated memory usage in MB (optional)
            
        Returns:
            True if streaming processing is recommended
            
        Raises:
            MemoryError: If memory assessment fails
        """
        pass
    
    @abstractmethod
    def get_memory_usage(self) -> MemoryUsage:
        """
        Get current memory usage statistics.
        
        Returns:
            MemoryUsage object with current memory statistics
            
        Raises:
            MemoryError: If memory usage cannot be determined
        """
        pass
    
    @abstractmethod
    def optimize_memory(self, force_gc: bool = False) -> bool:
        """
        Optimize memory usage by cleaning up unused objects.
        
        Args:
            force_gc: Force garbage collection
            
        Returns:
            True if optimization was successful
            
        Raises:
            MemoryError: If optimization fails
        """
        pass
    
    @abstractmethod
    def get_optimal_batch_size(self, item_size_mb: float, total_items: int) -> int:
        """
        Calculate optimal batch size based on available memory.
        
        Args:
            item_size_mb: Estimated size per item in MB
            total_items: Total number of items to process
            
        Returns:
            Optimal batch size for processing
            
        Raises:
            MemoryError: If calculation fails
        """
        pass
    
    @abstractmethod
    def monitor_memory_pressure(self) -> MemoryPressure:
        """
        Monitor current memory pressure level.
        
        Returns:
            Current memory pressure level
            
        Raises:
            MemoryError: If pressure monitoring fails
        """
        pass
    
    @abstractmethod
    def estimate_processing_memory(self, item_count: int, item_size_mb: float) -> float:
        """
        Estimate memory requirements for processing operation.
        
        Args:
            item_count: Number of items to process
            item_size_mb: Estimated size per item in MB
            
        Returns:
            Estimated total memory requirement in MB
            
        Raises:
            MemoryError: If estimation fails
        """
        pass
    
    @abstractmethod
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
            
        Raises:
            MemoryError: If recommendation cannot be generated
        """
        pass
    
    @abstractmethod
    def set_memory_thresholds(self, thresholds: MemoryThresholds) -> None:
        """
        Update memory threshold configuration.
        
        Args:
            thresholds: New memory threshold settings
            
        Raises:
            ValidationError: If thresholds are invalid
        """
        pass
    
    @abstractmethod
    def register_memory_callback(self, 
                                pressure_level: MemoryPressure, 
                                callback: Callable[[], None]) -> None:
        """
        Register callback for memory pressure events.
        
        Args:
            pressure_level: Memory pressure level to monitor
            callback: Function to call when pressure level is reached
            
        Raises:
            ValidationError: If callback registration fails
        """
        pass
    
    def check_memory_safety(self, operation_mb: float) -> bool:
        """
        Check if operation is safe to perform given current memory state.
        
        Args:
            operation_mb: Estimated memory requirement for operation
            
        Returns:
            True if operation is safe to perform
        """
        current_usage = self.get_memory_usage()
        projected_usage = current_usage.current_mb + operation_mb
        
        # Use critical threshold as safety limit
        thresholds = getattr(self, '_thresholds', MemoryThresholds())
        return projected_usage < thresholds.critical_threshold_mb