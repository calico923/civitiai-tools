"""
AdaptiveThresholds - Dynamic memory threshold management.

This module provides adaptive threshold adjustment based on system conditions
and historical memory usage patterns for optimal performance.
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, replace
from collections import deque

import sys
from pathlib import Path

# Add the src directory to the path for importing
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from core.interfaces.memory_manager import MemoryThresholds, MemoryPressure


@dataclass
class MemoryHistoryEntry:
    """Historical memory usage entry."""
    timestamp: float
    current_mb: float
    available_mb: float
    pressure_level: MemoryPressure
    operation_type: str


@dataclass
class ThresholdAdjustment:
    """Threshold adjustment recommendation."""
    streaming_threshold_mb: float
    warning_threshold_mb: float
    critical_threshold_mb: float
    adjustment_reason: str
    confidence: float


class AdaptiveThresholds:
    """
    Adaptive threshold management system.
    
    This class dynamically adjusts memory thresholds based on system conditions,
    historical usage patterns, and performance metrics to optimize memory usage.
    """
    
    def __init__(self, base_thresholds: Optional[MemoryThresholds] = None):
        """
        Initialize adaptive threshold manager.
        
        Args:
            base_thresholds: Base thresholds to start with, uses defaults if None
        """
        self._base_thresholds = base_thresholds or MemoryThresholds()
        self._current_thresholds = replace(self._base_thresholds)
        
        # History tracking
        self._memory_history = deque(maxlen=100)  # Keep last 100 entries
        self._adjustment_history = deque(maxlen=50)  # Keep last 50 adjustments
        
        # Learning parameters
        self._learning_rate = 0.1
        self._stability_factor = 0.8
        self._pressure_weights = {
            MemoryPressure.LOW: 1.0,
            MemoryPressure.MEDIUM: 0.8,
            MemoryPressure.HIGH: 0.6,
            MemoryPressure.CRITICAL: 0.4
        }
    
    def get_current_thresholds(self) -> MemoryThresholds:
        """
        Get current adaptive thresholds.
        
        Returns:
            Current memory thresholds
        """
        return replace(self._current_thresholds)
    
    def adjust_thresholds(self, 
                         current_memory_mb: float, 
                         available_memory_mb: float,
                         operation_type: str = "general") -> MemoryThresholds:
        """
        Adjust thresholds based on current memory conditions.
        
        Args:
            current_memory_mb: Current memory usage in MB
            available_memory_mb: Available memory in MB
            operation_type: Type of operation being performed
            
        Returns:
            Adjusted memory thresholds
        """
        # Record current memory state
        pressure_level = self._calculate_pressure_level(current_memory_mb, available_memory_mb)
        
        history_entry = MemoryHistoryEntry(
            timestamp=time.time(),
            current_mb=current_memory_mb,
            available_mb=available_memory_mb,
            pressure_level=pressure_level,
            operation_type=operation_type
        )
        self._memory_history.append(history_entry)
        
        # Calculate adjustment based on various factors
        adjustment = self._calculate_adjustment(
            current_memory_mb,
            available_memory_mb,
            pressure_level,
            operation_type
        )
        
        # Apply adjustment with stability factor
        new_thresholds = self._apply_adjustment(adjustment)
        
        # Validate and update thresholds
        validated_thresholds = self._validate_thresholds(new_thresholds)
        self._current_thresholds = validated_thresholds
        
        # Record adjustment
        self._adjustment_history.append(adjustment)
        
        return replace(validated_thresholds)
    
    def learn_from_performance(self, 
                              operation_success: bool,
                              operation_memory_mb: float,
                              operation_type: str) -> None:
        """
        Learn from operation performance to improve future threshold decisions.
        
        Args:
            operation_success: Whether the operation completed successfully
            operation_memory_mb: Memory used by the operation
            operation_type: Type of operation performed
        """
        if not self._memory_history:
            return
        
        # Get recent memory state during operation
        recent_entry = self._memory_history[-1]
        
        # Adjust learning based on success/failure
        if operation_success:
            # Operation succeeded - we can be more aggressive with memory usage
            if operation_memory_mb < self._current_thresholds.streaming_threshold_mb:
                self._adjust_threshold_component("streaming", 1.05)  # Increase by 5%
        else:
            # Operation failed - be more conservative
            if operation_memory_mb > self._current_thresholds.streaming_threshold_mb * 0.8:
                self._adjust_threshold_component("streaming", 0.95)  # Decrease by 5%
    
    def get_threshold_statistics(self) -> Dict[str, float]:
        """
        Get statistics about threshold adjustments and memory usage.
        
        Returns:
            Dictionary with threshold statistics
        """
        if not self._memory_history:
            return {}
        
        # Calculate statistics from memory history
        recent_entries = list(self._memory_history)[-20:]  # Last 20 entries
        
        avg_memory = sum(entry.current_mb for entry in recent_entries) / len(recent_entries)
        avg_available = sum(entry.available_mb for entry in recent_entries) / len(recent_entries)
        
        pressure_counts = {pressure: 0 for pressure in MemoryPressure}
        for entry in recent_entries:
            pressure_counts[entry.pressure_level] += 1
        
        adjustment_count = len(self._adjustment_history)
        
        return {
            'average_memory_mb': avg_memory,
            'average_available_mb': avg_available,
            'high_pressure_percentage': (pressure_counts[MemoryPressure.HIGH] + 
                                       pressure_counts[MemoryPressure.CRITICAL]) / len(recent_entries) * 100,
            'total_adjustments': adjustment_count,
            'current_streaming_threshold': self._current_thresholds.streaming_threshold_mb,
            'current_warning_threshold': self._current_thresholds.warning_threshold_mb,
            'current_critical_threshold': self._current_thresholds.critical_threshold_mb
        }
    
    def reset_to_defaults(self) -> None:
        """Reset thresholds to default values."""
        self._current_thresholds = replace(self._base_thresholds)
        self._memory_history.clear()
        self._adjustment_history.clear()
    
    def _calculate_pressure_level(self, current_mb: float, available_mb: float) -> MemoryPressure:
        """Calculate memory pressure level based on current thresholds."""
        if current_mb > self._current_thresholds.critical_threshold_mb or available_mb < 100:
            return MemoryPressure.CRITICAL
        elif current_mb > self._current_thresholds.warning_threshold_mb or available_mb < 500:
            return MemoryPressure.HIGH
        elif current_mb > self._current_thresholds.streaming_threshold_mb or available_mb < 1000:
            return MemoryPressure.MEDIUM
        else:
            return MemoryPressure.LOW
    
    def _calculate_adjustment(self, 
                            current_memory_mb: float,
                            available_memory_mb: float,
                            pressure_level: MemoryPressure,
                            operation_type: str) -> ThresholdAdjustment:
        """Calculate threshold adjustment based on current conditions."""
        
        # Base adjustment factors
        memory_utilization = current_memory_mb / (current_memory_mb + available_memory_mb)
        pressure_weight = self._pressure_weights.get(pressure_level, 1.0)
        
        # Calculate adjustment ratios
        if pressure_level == MemoryPressure.CRITICAL:
            # Very conservative - reduce thresholds significantly
            streaming_ratio = 0.8
            warning_ratio = 0.85
            critical_ratio = 0.9
            reason = "Critical pressure - reducing thresholds"
            confidence = 0.9
        elif pressure_level == MemoryPressure.HIGH:
            # Conservative - reduce thresholds moderately
            streaming_ratio = 0.9
            warning_ratio = 0.92
            critical_ratio = 0.95
            reason = "High pressure - moderately reducing thresholds"
            confidence = 0.8
        elif pressure_level == MemoryPressure.MEDIUM:
            # Balanced - small adjustments
            streaming_ratio = 0.95 if memory_utilization > 0.7 else 1.05
            warning_ratio = 0.98 if memory_utilization > 0.7 else 1.02
            critical_ratio = 0.99 if memory_utilization > 0.7 else 1.01
            reason = "Medium pressure - fine-tuning thresholds"
            confidence = 0.7
        else:  # LOW pressure
            # Aggressive - can increase thresholds
            streaming_ratio = 1.1 if available_memory_mb > 2000 else 1.05
            warning_ratio = 1.05 if available_memory_mb > 2000 else 1.02
            critical_ratio = 1.03 if available_memory_mb > 2000 else 1.01
            reason = "Low pressure - increasing thresholds for better performance"
            confidence = 0.6
        
        # Apply adjustments to current thresholds
        new_streaming = self._current_thresholds.streaming_threshold_mb * streaming_ratio
        new_warning = self._current_thresholds.warning_threshold_mb * warning_ratio
        new_critical = self._current_thresholds.critical_threshold_mb * critical_ratio
        
        return ThresholdAdjustment(
            streaming_threshold_mb=new_streaming,
            warning_threshold_mb=new_warning,
            critical_threshold_mb=new_critical,
            adjustment_reason=reason,
            confidence=confidence
        )
    
    def _apply_adjustment(self, adjustment: ThresholdAdjustment) -> MemoryThresholds:
        """Apply adjustment with stability factor to prevent oscillation."""
        
        # Apply stability factor to smooth adjustments
        streaming_delta = (adjustment.streaming_threshold_mb - 
                          self._current_thresholds.streaming_threshold_mb) * self._learning_rate
        warning_delta = (adjustment.warning_threshold_mb - 
                        self._current_thresholds.warning_threshold_mb) * self._learning_rate
        critical_delta = (adjustment.critical_threshold_mb - 
                         self._current_thresholds.critical_threshold_mb) * self._learning_rate
        
        new_streaming = self._current_thresholds.streaming_threshold_mb + streaming_delta
        new_warning = self._current_thresholds.warning_threshold_mb + warning_delta
        new_critical = self._current_thresholds.critical_threshold_mb + critical_delta
        
        return MemoryThresholds(
            streaming_threshold_mb=new_streaming,
            warning_threshold_mb=new_warning,
            critical_threshold_mb=new_critical,
            max_batch_size=self._current_thresholds.max_batch_size,
            min_batch_size=self._current_thresholds.min_batch_size
        )
    
    def _validate_thresholds(self, thresholds: MemoryThresholds) -> MemoryThresholds:
        """Validate and correct threshold values to maintain logical ordering."""
        
        # Ensure minimum values
        streaming_mb = max(50.0, thresholds.streaming_threshold_mb)
        warning_mb = max(streaming_mb + 50.0, thresholds.warning_threshold_mb)
        critical_mb = max(warning_mb + 50.0, thresholds.critical_threshold_mb)
        
        # Ensure maximum values (don't exceed reasonable limits)
        streaming_mb = min(2000.0, streaming_mb)
        warning_mb = min(4000.0, warning_mb)
        critical_mb = min(8000.0, critical_mb)
        
        return MemoryThresholds(
            streaming_threshold_mb=streaming_mb,
            warning_threshold_mb=warning_mb,
            critical_threshold_mb=critical_mb,
            max_batch_size=thresholds.max_batch_size,
            min_batch_size=thresholds.min_batch_size
        )
    
    def _adjust_threshold_component(self, component: str, ratio: float) -> None:
        """Adjust a specific threshold component."""
        if component == "streaming":
            self._current_thresholds.streaming_threshold_mb *= ratio
        elif component == "warning":
            self._current_thresholds.warning_threshold_mb *= ratio
        elif component == "critical":
            self._current_thresholds.critical_threshold_mb *= ratio
        
        # Re-validate after adjustment
        self._current_thresholds = self._validate_thresholds(self._current_thresholds)