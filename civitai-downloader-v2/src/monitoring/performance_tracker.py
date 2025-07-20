#!/usr/bin/env python3
"""
Performance Tracker for CivitAI Downloader.
Provides performance monitoring, regression detection, and baseline comparison.
"""

import time
import threading
import statistics
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class PerformanceBaseline:
    """Performance baseline data."""
    operation: str
    avg: float
    min: float
    max: float
    count: int
    stddev: float
    established_at: float


@dataclass
class RegressionResult:
    """Performance regression analysis result."""
    is_regression: bool
    is_improvement: bool
    current_value: float
    baseline_avg: float
    regression_factor: float
    improvement_factor: float
    threshold_exceeded: bool


class PerformanceTracker:
    """Advanced performance tracking with regression detection and baseline management."""
    
    def __init__(self, regression_threshold: float = 1.5, improvement_threshold: float = 0.7):
        """
        Initialize performance tracker.
        
        Args:
            regression_threshold: Factor above baseline considered regression (e.g., 1.5 = 50% slower)
            improvement_threshold: Factor below baseline considered improvement (e.g., 0.7 = 30% faster)
        """
        self.regression_threshold = regression_threshold
        self.improvement_threshold = improvement_threshold
        
        # Performance data storage
        self.performance_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.baselines: Dict[str, PerformanceBaseline] = {}
        
        # Real-time tracking
        self.recent_measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self.operation_counts: Dict[str, int] = defaultdict(int)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Statistics
        self.tracker_stats = {
            'total_measurements': 0,
            'operations_tracked': 0,
            'regressions_detected': 0,
            'improvements_detected': 0,
            'baselines_established': 0
        }
    
    def record_performance(self, operation: str, duration_ms: float, 
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record performance measurement for an operation.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            metadata: Optional metadata about the operation
        """
        measurement = {
            'duration_ms': duration_ms,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        
        with self._lock:
            self.performance_data[operation].append(measurement)
            self.recent_measurements[operation].append(measurement)
            self.operation_counts[operation] += 1
            self.tracker_stats['total_measurements'] += 1
            
            # Update operations count
            if operation not in self.performance_data or len(self.performance_data[operation]) == 1:
                self.tracker_stats['operations_tracked'] += 1
    
    def establish_baseline(self, operation: str, min_samples: int = 5) -> Optional[PerformanceBaseline]:
        """
        Establish performance baseline for an operation.
        
        Args:
            operation: Operation name
            min_samples: Minimum number of samples required for baseline
            
        Returns:
            PerformanceBaseline if established, None if insufficient data
        """
        with self._lock:
            if operation not in self.performance_data:
                return None
            
            measurements = list(self.performance_data[operation])
            
            if len(measurements) < min_samples:
                return None
            
            # Extract duration values
            durations = [m['duration_ms'] for m in measurements]
            
            # Calculate baseline statistics
            baseline = PerformanceBaseline(
                operation=operation,
                avg=statistics.mean(durations),
                min=min(durations),
                max=max(durations),
                count=len(durations),
                stddev=statistics.stdev(durations) if len(durations) > 1 else 0,
                established_at=time.time()
            )
            
            self.baselines[operation] = baseline
            self.tracker_stats['baselines_established'] += 1
            
            return baseline
    
    def get_baseline(self, operation: str) -> Optional[PerformanceBaseline]:
        """
        Get performance baseline for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            PerformanceBaseline if exists, None otherwise
        """
        with self._lock:
            return self.baselines.get(operation)
    
    def check_regression(self, operation: str, current_duration: float) -> RegressionResult:
        """
        Check if current performance indicates regression or improvement.
        
        Args:
            operation: Operation name
            current_duration: Current operation duration in milliseconds
            
        Returns:
            RegressionResult with analysis
        """
        baseline = self.get_baseline(operation)
        
        if not baseline:
            # Auto-establish baseline if we have enough data
            baseline = self.establish_baseline(operation)
            if not baseline:
                # No baseline available
                return RegressionResult(
                    is_regression=False,
                    is_improvement=False,
                    current_value=current_duration,
                    baseline_avg=0,
                    regression_factor=1.0,
                    improvement_factor=1.0,
                    threshold_exceeded=False
                )
        
        # Calculate performance factors
        regression_factor = current_duration / baseline.avg
        improvement_factor = current_duration / baseline.avg
        
        # Determine if this is a regression or improvement
        is_regression = regression_factor >= self.regression_threshold
        is_improvement = improvement_factor <= self.improvement_threshold
        
        # Check if any threshold is exceeded
        threshold_exceeded = is_regression or is_improvement
        
        # Update statistics
        with self._lock:
            if is_regression:
                self.tracker_stats['regressions_detected'] += 1
            elif is_improvement:
                self.tracker_stats['improvements_detected'] += 1
        
        return RegressionResult(
            is_regression=is_regression,
            is_improvement=is_improvement,
            current_value=current_duration,
            baseline_avg=baseline.avg,
            regression_factor=regression_factor,
            improvement_factor=improvement_factor,
            threshold_exceeded=threshold_exceeded
        )
    
    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """
        Get detailed statistics for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Operation statistics
        """
        with self._lock:
            if operation not in self.performance_data:
                return {'error': 'Operation not found'}
            
            measurements = list(self.performance_data[operation])
            recent_measurements = list(self.recent_measurements[operation])
            
            durations = [m['duration_ms'] for m in measurements]
            recent_durations = [m['duration_ms'] for m in recent_measurements]
            
            stats = {
                'operation': operation,
                'total_measurements': len(measurements),
                'recent_measurements': len(recent_measurements),
                'all_time_stats': {
                    'avg': statistics.mean(durations),
                    'min': min(durations),
                    'max': max(durations),
                    'median': statistics.median(durations),
                    'stddev': statistics.stdev(durations) if len(durations) > 1 else 0
                }
            }
            
            # Recent performance (last 50 measurements)
            if recent_durations:
                stats['recent_stats'] = {
                    'avg': statistics.mean(recent_durations),
                    'min': min(recent_durations),
                    'max': max(recent_durations),
                    'median': statistics.median(recent_durations),
                    'stddev': statistics.stdev(recent_durations) if len(recent_durations) > 1 else 0
                }
                
                # Performance trend (recent vs all-time)
                recent_avg = stats['recent_stats']['avg']
                all_time_avg = stats['all_time_stats']['avg']
                trend_factor = recent_avg / all_time_avg
                
                stats['performance_trend'] = {
                    'factor': trend_factor,
                    'direction': 'improving' if trend_factor < 0.95 else 'degrading' if trend_factor > 1.05 else 'stable',
                    'change_percent': ((trend_factor - 1) * 100)
                }
            
            # Baseline information
            if operation in self.baselines:
                baseline = self.baselines[operation]
                stats['baseline'] = {
                    'avg': baseline.avg,
                    'established_at': baseline.established_at,
                    'sample_count': baseline.count,
                    'age_hours': (time.time() - baseline.established_at) / 3600
                }
        
        return stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get overall performance tracking summary.
        
        Returns:
            Performance summary across all operations
        """
        with self._lock:
            operations = list(self.performance_data.keys())
            
            # Calculate summary statistics
            total_measurements = sum(len(measurements) for measurements in self.performance_data.values())
            
            # Most active operations
            operation_activity = [
                (op, len(self.performance_data[op])) 
                for op in operations
            ]
            operation_activity.sort(key=lambda x: x[1], reverse=True)
            
            # Recent performance trends
            trends = {}
            for operation in operations[:10]:  # Top 10 operations
                stats = self.get_operation_stats(operation)
                if 'performance_trend' in stats:
                    trends[operation] = stats['performance_trend']
            
            summary = {
                'tracking_summary': {
                    'total_operations': len(operations),
                    'total_measurements': total_measurements,
                    'baselines_established': len(self.baselines),
                    'avg_measurements_per_operation': total_measurements / len(operations) if operations else 0
                },
                'most_active_operations': operation_activity[:10],
                'performance_trends': trends,
                'tracker_statistics': self.tracker_stats.copy()
            }
        
        return summary
    
    def get_recent_performance(self, operation: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get recent performance measurements for an operation.
        
        Args:
            operation: Operation name
            minutes: Number of minutes to look back
            
        Returns:
            List of recent measurements
        """
        cutoff_time = time.time() - (minutes * 60)
        
        with self._lock:
            if operation not in self.performance_data:
                return []
            
            measurements = list(self.performance_data[operation])
            recent = [
                m for m in measurements 
                if m['timestamp'] >= cutoff_time
            ]
        
        return recent
    
    def clear_performance_data(self, operation: Optional[str] = None) -> None:
        """
        Clear performance data for an operation or all operations.
        
        Args:
            operation: Operation name to clear, or None to clear all
        """
        with self._lock:
            if operation:
                if operation in self.performance_data:
                    self.performance_data[operation].clear()
                    self.recent_measurements[operation].clear()
                    self.operation_counts[operation] = 0
                if operation in self.baselines:
                    del self.baselines[operation]
            else:
                self.performance_data.clear()
                self.recent_measurements.clear()
                self.operation_counts.clear()
                self.baselines.clear()
                
                # Reset statistics
                self.tracker_stats = {
                    'total_measurements': 0,
                    'operations_tracked': 0,
                    'regressions_detected': 0,
                    'improvements_detected': 0,
                    'baselines_established': 0
                }
    
    def configure_thresholds(self, regression_threshold: float, improvement_threshold: float) -> None:
        """
        Configure regression and improvement thresholds.
        
        Args:
            regression_threshold: Factor above baseline considered regression
            improvement_threshold: Factor below baseline considered improvement
        """
        with self._lock:
            self.regression_threshold = regression_threshold
            self.improvement_threshold = improvement_threshold
    
    def export_performance_data(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Export performance data for analysis.
        
        Args:
            operation: Specific operation to export, or None for all
            
        Returns:
            Exported performance data
        """
        with self._lock:
            export_data = {
                'export_timestamp': time.time(),
                'tracker_config': {
                    'regression_threshold': self.regression_threshold,
                    'improvement_threshold': self.improvement_threshold
                },
                'statistics': self.tracker_stats.copy(),
                'baselines': {},
                'performance_data': {}
            }
            
            operations = [operation] if operation else list(self.performance_data.keys())
            
            for op in operations:
                if op in self.performance_data:
                    export_data['performance_data'][op] = list(self.performance_data[op])
                
                if op in self.baselines:
                    baseline = self.baselines[op]
                    export_data['baselines'][op] = {
                        'avg': baseline.avg,
                        'min': baseline.min,
                        'max': baseline.max,
                        'count': baseline.count,
                        'stddev': baseline.stddev,
                        'established_at': baseline.established_at
                    }
        
        return export_data