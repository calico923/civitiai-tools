"""
ErrorStatistics - Error tracking and statistical analysis.

This module provides comprehensive error statistics tracking for monitoring
system health and identifying patterns in error occurrences.
"""

import time
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ErrorEvent:
    """Individual error event record."""
    timestamp: float
    category: str
    error_type: str
    component: str
    operation: str
    message: str
    context: Dict[str, Any]


class ErrorStatistics:
    """
    Comprehensive error statistics tracking and analysis.
    
    This class tracks error occurrences, provides statistical analysis,
    and helps identify patterns for system monitoring and debugging.
    """
    
    def __init__(self, max_events: int = 10000):
        """
        Initialize error statistics tracker.
        
        Args:
            max_events: Maximum number of events to keep in memory
        """
        self.max_events = max_events
        self.error_events = deque(maxlen=max_events)
        
        # Statistical counters
        self.total_errors = 0
        self.category_counts = defaultdict(int)
        self.type_counts = defaultdict(int)
        self.component_counts = defaultdict(int)
        self.operation_counts = defaultdict(int)
        
        # Time-based tracking
        self.hourly_counts = defaultdict(int)
        self.daily_counts = defaultdict(int)
        
        # Error rate tracking
        self.last_reset_time = time.time()
        self.errors_since_reset = 0
    
    def record_error(self, category: str, error_type: str, component: str, 
                    operation: str = 'unknown', message: str = '', 
                    context: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an error event.
        
        Args:
            category: Error category (NETWORK, API, VALIDATION, etc.)
            error_type: Specific error type (ConnectionError, ValueError, etc.)
            component: Component where error occurred
            operation: Operation being performed when error occurred
            message: Error message
            context: Additional context information
        """
        timestamp = time.time()
        
        # Create error event
        event = ErrorEvent(
            timestamp=timestamp,
            category=category,
            error_type=error_type,
            component=component,
            operation=operation,
            message=message,
            context=context or {}
        )
        
        # Store event
        self.error_events.append(event)
        
        # Update counters
        self.total_errors += 1
        self.category_counts[category] += 1
        self.type_counts[error_type] += 1
        self.component_counts[component] += 1
        self.operation_counts[operation] += 1
        
        # Update time-based tracking
        hour_key = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d-%H')
        day_key = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        self.hourly_counts[hour_key] += 1
        self.daily_counts[day_key] += 1
        
        # Update error rate tracking
        self.errors_since_reset += 1
    
    def get_statistics(self, time_window: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive error statistics.
        
        Args:
            time_window: Time window in seconds (None for all time)
            
        Returns:
            Dictionary containing error statistics
        """
        if time_window:
            cutoff_time = time.time() - time_window
            relevant_events = [e for e in self.error_events if e.timestamp >= cutoff_time]
        else:
            relevant_events = list(self.error_events)
        
        if not relevant_events:
            return {
                'total_errors': 0,
                'error_categories': {},
                'error_types': {},
                'components': {},
                'operations': {},
                'error_rate': 0.0,
                'time_window': time_window
            }
        
        # Calculate statistics for relevant events
        category_stats = defaultdict(int)
        type_stats = defaultdict(int)
        component_stats = defaultdict(int)
        operation_stats = defaultdict(int)
        
        for event in relevant_events:
            category_stats[event.category] += 1
            type_stats[event.error_type] += 1
            component_stats[event.component] += 1
            operation_stats[event.operation] += 1
        
        # Calculate error rate
        if time_window and time_window > 0:
            error_rate = len(relevant_events) / time_window
        else:
            total_time = time.time() - self.last_reset_time
            error_rate = self.total_errors / max(total_time, 1)
        
        return {
            'total_errors': len(relevant_events),
            'error_categories': dict(category_stats),
            'error_types': dict(type_stats),
            'components': dict(component_stats),
            'operations': dict(operation_stats),
            'error_rate': error_rate,
            'time_window': time_window
        }
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error trends over the specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Trend analysis data
        """
        cutoff_time = time.time() - (hours * 3600)
        recent_events = [e for e in self.error_events if e.timestamp >= cutoff_time]
        
        if not recent_events:
            return {
                'total_errors': 0,
                'hourly_distribution': {},
                'trend_direction': 'stable',
                'peak_hour': None,
                'average_per_hour': 0.0
            }
        
        # Group by hour
        hourly_distribution = defaultdict(int)
        for event in recent_events:
            hour_key = datetime.fromtimestamp(event.timestamp).strftime('%H:00')
            hourly_distribution[hour_key] += 1
        
        # Calculate trend
        if len(hourly_distribution) >= 2:
            hours_sorted = sorted(hourly_distribution.keys())
            first_half = sum(hourly_distribution[h] for h in hours_sorted[:len(hours_sorted)//2])
            second_half = sum(hourly_distribution[h] for h in hours_sorted[len(hours_sorted)//2:])
            
            if second_half > first_half * 1.2:
                trend_direction = 'increasing'
            elif second_half < first_half * 0.8:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'
        else:
            trend_direction = 'insufficient_data'
        
        # Find peak hour
        peak_hour = max(hourly_distribution.keys(), key=lambda h: hourly_distribution[h]) \
                   if hourly_distribution else None
        
        return {
            'total_errors': len(recent_events),
            'hourly_distribution': dict(hourly_distribution),
            'trend_direction': trend_direction,
            'peak_hour': peak_hour,
            'average_per_hour': len(recent_events) / hours
        }
    
    def get_top_errors(self, limit: int = 10, by: str = 'type') -> List[Dict[str, Any]]:
        """
        Get top errors by frequency.
        
        Args:
            limit: Maximum number of results
            by: Group by 'type', 'category', 'component', or 'operation'
            
        Returns:
            List of top errors with counts
        """
        if by == 'type':
            counts = self.type_counts
        elif by == 'category':
            counts = self.category_counts
        elif by == 'component':
            counts = self.component_counts
        elif by == 'operation':
            counts = self.operation_counts
        else:
            raise ValueError(f"Invalid 'by' parameter: {by}")
        
        # Sort by count and take top N
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'name': name, 'count': count, 'percentage': (count / self.total_errors) * 100}
            for name, count in sorted_items[:limit]
        ]
    
    def get_error_rate(self, time_window: int = 3600) -> float:
        """
        Get current error rate (errors per second).
        
        Args:
            time_window: Time window in seconds
            
        Returns:
            Error rate (errors per second)
        """
        cutoff_time = time.time() - time_window
        recent_errors = sum(1 for e in self.error_events if e.timestamp >= cutoff_time)
        return recent_errors / time_window
    
    def is_error_spike(self, threshold_multiplier: float = 3.0, 
                      base_window: int = 3600, spike_window: int = 300) -> bool:
        """
        Detect if there's an error spike.
        
        Args:
            threshold_multiplier: Spike threshold as multiple of baseline
            base_window: Baseline calculation window in seconds
            spike_window: Spike detection window in seconds
            
        Returns:
            True if error spike is detected
        """
        current_time = time.time()
        
        # Get baseline error rate
        baseline_start = current_time - base_window - spike_window
        baseline_end = current_time - spike_window
        baseline_errors = sum(1 for e in self.error_events 
                            if baseline_start <= e.timestamp < baseline_end)
        baseline_rate = baseline_errors / base_window
        
        # Get current spike window rate
        spike_start = current_time - spike_window
        spike_errors = sum(1 for e in self.error_events if e.timestamp >= spike_start)
        spike_rate = spike_errors / spike_window
        
        # Check if spike exceeds threshold
        threshold = baseline_rate * threshold_multiplier
        return spike_rate > threshold and spike_errors > 5  # At least 5 errors
    
    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self.error_events.clear()
        self.total_errors = 0
        self.category_counts.clear()
        self.type_counts.clear()
        self.component_counts.clear()
        self.operation_counts.clear()
        self.hourly_counts.clear()
        self.daily_counts.clear()
        self.last_reset_time = time.time()
        self.errors_since_reset = 0
    
    def export_events(self, time_window: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Export error events for external analysis.
        
        Args:
            time_window: Time window in seconds (None for all events)
            
        Returns:
            List of error event dictionaries
        """
        if time_window:
            cutoff_time = time.time() - time_window
            relevant_events = [e for e in self.error_events if e.timestamp >= cutoff_time]
        else:
            relevant_events = list(self.error_events)
        
        return [
            {
                'timestamp': event.timestamp,
                'datetime': datetime.fromtimestamp(event.timestamp).isoformat(),
                'category': event.category,
                'error_type': event.error_type,
                'component': event.component,
                'operation': event.operation,
                'message': event.message,
                'context': event.context
            }
            for event in relevant_events
        ]