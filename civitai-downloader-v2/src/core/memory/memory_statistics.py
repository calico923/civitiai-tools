"""
MemoryStatistics - Memory usage statistics collection and analysis.

This module provides comprehensive memory statistics tracking, collection,
and analysis for performance monitoring and optimization.
"""

import time
import statistics
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
from datetime import datetime, timedelta

import sys
from pathlib import Path

# Add the src directory to the path for importing
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from core.interfaces.memory_manager import MemoryPressure


@dataclass
class MemoryEvent:
    """Memory event record for statistics tracking."""
    timestamp: float
    event_type: str
    memory_before_mb: float
    memory_after_mb: float
    memory_delta_mb: float
    context: Dict[str, Any]
    operation_duration: Optional[float] = None


@dataclass
class MemoryAggregateStats:
    """Aggregated memory statistics."""
    total_events: int
    average_memory_usage: float
    peak_memory_usage: float
    memory_savings: float
    pressure_distribution: Dict[str, int]
    operation_efficiency: float


class MemoryStatistics:
    """
    Memory statistics collection and analysis system.
    
    This class tracks memory events, calculates aggregated statistics,
    and provides insights for memory usage optimization.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize memory statistics tracker.
        
        Args:
            max_history: Maximum number of events to keep in history
        """
        self._max_history = max_history
        self._memory_events = deque(maxlen=max_history)
        self._pressure_history = deque(maxlen=max_history)
        
        # Performance tracking
        self._operation_stats = defaultdict(list)
        self._efficiency_metrics = {}
        
        # Aggregated statistics cache
        self._last_aggregation_time = 0
        self._cached_aggregation = None
        self._aggregation_cache_duration = 60  # Cache for 60 seconds
    
    def record_memory_event(self, 
                           event_type: str,
                           memory_before_mb: float,
                           memory_after_mb: float,
                           context: Optional[Dict[str, Any]] = None,
                           operation_duration: Optional[float] = None) -> None:
        """
        Record a memory event for statistics tracking.
        
        Args:
            event_type: Type of memory event (e.g., 'optimization', 'allocation', 'cleanup')
            memory_before_mb: Memory usage before the event
            memory_after_mb: Memory usage after the event
            context: Additional context information
            operation_duration: Duration of the operation in seconds
        """
        timestamp = time.time()
        memory_delta = memory_after_mb - memory_before_mb
        
        event = MemoryEvent(
            timestamp=timestamp,
            event_type=event_type,
            memory_before_mb=memory_before_mb,
            memory_after_mb=memory_after_mb,
            memory_delta_mb=memory_delta,
            context=context or {},
            operation_duration=operation_duration
        )
        
        self._memory_events.append(event)
        
        # Track operation-specific statistics
        self._operation_stats[event_type].append({
            'memory_delta': memory_delta,
            'duration': operation_duration,
            'efficiency': self._calculate_efficiency(memory_delta, operation_duration)
        })
        
        # Invalidate aggregation cache
        self._cached_aggregation = None
    
    def record_pressure_event(self, 
                            pressure_level: MemoryPressure,
                            current_memory_mb: float,
                            context: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a memory pressure event.
        
        Args:
            pressure_level: Current memory pressure level
            current_memory_mb: Current memory usage in MB
            context: Additional context information
        """
        pressure_event = {
            'timestamp': time.time(),
            'pressure_level': pressure_level.value,
            'memory_mb': current_memory_mb,
            'context': context or {}
        }
        
        self._pressure_history.append(pressure_event)
    
    def get_recent_statistics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent memory statistics events.
        
        Args:
            limit: Maximum number of recent events to return
            
        Returns:
            List of recent memory events as dictionaries
        """
        recent_events = list(self._memory_events)[-limit:]
        return [self._event_to_dict(event) for event in recent_events]
    
    def get_aggregated_statistics(self) -> Dict[str, Any]:
        """
        Get aggregated memory statistics.
        
        Returns:
            Dictionary with aggregated memory statistics
        """
        current_time = time.time()
        
        # Use cached aggregation if still valid
        if (self._cached_aggregation and 
            current_time - self._last_aggregation_time < self._aggregation_cache_duration):
            return self._cached_aggregation
        
        # Calculate fresh aggregation
        aggregation = self._calculate_aggregated_statistics()
        
        # Cache the result
        self._cached_aggregation = aggregation
        self._last_aggregation_time = current_time
        
        return aggregation
    
    def get_operation_statistics(self, operation_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for specific operation types.
        
        Args:
            operation_type: Specific operation type to analyze, or None for all
            
        Returns:
            Dictionary with operation-specific statistics
        """
        if operation_type:
            if operation_type not in self._operation_stats:
                return {}
            
            stats = self._operation_stats[operation_type]
            return self._calculate_operation_stats(operation_type, stats)
        else:
            # Return statistics for all operation types
            all_stats = {}
            for op_type, stats in self._operation_stats.items():
                all_stats[op_type] = self._calculate_operation_stats(op_type, stats)
            return all_stats
    
    def get_pressure_distribution(self, hours: int = 24) -> Dict[str, float]:
        """
        Get memory pressure distribution over the specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with pressure level percentages
        """
        cutoff_time = time.time() - (hours * 3600)
        recent_pressure = [
            event for event in self._pressure_history
            if event['timestamp'] > cutoff_time
        ]
        
        if not recent_pressure:
            return {}
        
        # Count pressure levels
        pressure_counts = defaultdict(int)
        for event in recent_pressure:
            pressure_counts[event['pressure_level']] += 1
        
        total_events = len(recent_pressure)
        
        # Calculate percentages
        distribution = {}
        for pressure_level, count in pressure_counts.items():
            distribution[pressure_level] = (count / total_events) * 100
        
        return distribution
    
    def get_memory_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze memory usage trends over time.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with trend analysis
        """
        cutoff_time = time.time() - (hours * 3600)
        recent_events = [
            event for event in self._memory_events
            if event.timestamp > cutoff_time
        ]
        
        if not recent_events:
            return {}
        
        # Extract memory values over time
        memory_values = [event.memory_after_mb for event in recent_events]
        timestamps = [event.timestamp for event in recent_events]
        
        # Calculate trend metrics
        if len(memory_values) > 1:
            # Simple linear trend calculation
            time_diffs = [timestamps[i] - timestamps[0] for i in range(len(timestamps))]
            memory_diffs = [memory_values[i] - memory_values[0] for i in range(len(memory_values))]
            
            if time_diffs[-1] > 0:
                trend_slope = sum(t * m for t, m in zip(time_diffs, memory_diffs)) / sum(t * t for t in time_diffs)
            else:
                trend_slope = 0
        else:
            trend_slope = 0
        
        return {
            'average_memory_mb': statistics.mean(memory_values),
            'median_memory_mb': statistics.median(memory_values),
            'min_memory_mb': min(memory_values),
            'max_memory_mb': max(memory_values),
            'memory_range_mb': max(memory_values) - min(memory_values),
            'trend_slope_mb_per_hour': trend_slope * 3600,  # Convert to per hour
            'volatility': statistics.stdev(memory_values) if len(memory_values) > 1 else 0,
            'total_events': len(recent_events)
        }
    
    def export_statistics(self, format: str = 'dict') -> Union[Dict[str, Any], str]:
        """
        Export statistics in various formats.
        
        Args:
            format: Export format ('dict', 'json', 'csv')
            
        Returns:
            Statistics in requested format
        """
        stats = {
            'aggregated': self.get_aggregated_statistics(),
            'operations': self.get_operation_statistics(),
            'pressure_distribution': self.get_pressure_distribution(),
            'trends': self.get_memory_trends(),
            'export_timestamp': datetime.now().isoformat()
        }
        
        if format == 'dict':
            return stats
        elif format == 'json':
            import json
            return json.dumps(stats, indent=2)
        elif format == 'csv':
            # Simple CSV export of recent events
            csv_lines = ['timestamp,event_type,memory_before_mb,memory_after_mb,memory_delta_mb,duration']
            for event in self._memory_events:
                csv_lines.append(
                    f"{event.timestamp},{event.event_type},{event.memory_before_mb},"
                    f"{event.memory_after_mb},{event.memory_delta_mb},{event.operation_duration or ''}"
                )
            return '\n'.join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def clear_statistics(self) -> None:
        """Clear all collected statistics."""
        self._memory_events.clear()
        self._pressure_history.clear()
        self._operation_stats.clear()
        self._efficiency_metrics.clear()
        self._cached_aggregation = None
    
    def _event_to_dict(self, event: MemoryEvent) -> Dict[str, Any]:
        """Convert MemoryEvent to dictionary."""
        return {
            'timestamp': event.timestamp,
            'event_type': event.event_type,
            'memory_before_mb': event.memory_before_mb,
            'memory_after_mb': event.memory_after_mb,
            'memory_delta_mb': event.memory_delta_mb,
            'context': event.context,
            'operation_duration': event.operation_duration
        }
    
    def _calculate_aggregated_statistics(self) -> Dict[str, Any]:
        """Calculate aggregated statistics from all events."""
        if not self._memory_events:
            return {
                'total_events': 0,
                'average_memory_usage': 0.0,
                'peak_memory_usage': 0.0,
                'memory_savings': 0.0,
                'operation_efficiency': 0.0
            }
        
        # Basic aggregations
        memory_values = [event.memory_after_mb for event in self._memory_events]
        memory_deltas = [event.memory_delta_mb for event in self._memory_events]
        
        # Calculate pressure distribution
        pressure_distribution = self.get_pressure_distribution()
        
        # Calculate memory savings (sum of negative deltas)
        memory_savings = sum(delta for delta in memory_deltas if delta < 0)
        
        # Calculate operation efficiency (average across all operations)
        all_efficiencies = []
        for op_stats in self._operation_stats.values():
            efficiencies = [stat['efficiency'] for stat in op_stats if stat['efficiency'] is not None]
            all_efficiencies.extend(efficiencies)
        
        avg_efficiency = statistics.mean(all_efficiencies) if all_efficiencies else 0.0
        
        return {
            'total_events': len(self._memory_events),
            'average_memory_usage': statistics.mean(memory_values),
            'peak_memory_usage': max(memory_values),
            'memory_savings': abs(memory_savings),  # Report as positive value
            'pressure_distribution': pressure_distribution,
            'operation_efficiency': avg_efficiency
        }
    
    def _calculate_operation_stats(self, operation_type: str, stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for a specific operation type."""
        if not stats:
            return {}
        
        memory_deltas = [stat['memory_delta'] for stat in stats]
        durations = [stat['duration'] for stat in stats if stat['duration'] is not None]
        efficiencies = [stat['efficiency'] for stat in stats if stat['efficiency'] is not None]
        
        result = {
            'total_operations': len(stats),
            'average_memory_delta_mb': statistics.mean(memory_deltas),
            'total_memory_delta_mb': sum(memory_deltas),
            'memory_savings_mb': abs(sum(delta for delta in memory_deltas if delta < 0))
        }
        
        if durations:
            result.update({
                'average_duration_seconds': statistics.mean(durations),
                'total_duration_seconds': sum(durations)
            })
        
        if efficiencies:
            result['average_efficiency'] = statistics.mean(efficiencies)
        
        return result
    
    def _calculate_efficiency(self, memory_delta: float, duration: Optional[float]) -> Optional[float]:
        """Calculate operation efficiency metric."""
        if duration is None or duration <= 0:
            return None
        
        # Efficiency = |memory savings| / time
        # Positive for memory-saving operations, negative for memory-consuming operations
        if memory_delta < 0:  # Memory was saved
            return abs(memory_delta) / duration
        else:  # Memory was consumed
            return -memory_delta / duration