#!/usr/bin/env python3
"""
Metrics Collector for CivitAI Downloader.
Provides high-performance metrics collection with counters, gauges, and histograms.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional
import statistics


class MetricsCollector:
    """High-performance metrics collector for application monitoring."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._histogram_stats: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Thread safety
        self._counters_lock = threading.Lock()
        self._gauges_lock = threading.Lock()
        self._histograms_lock = threading.Lock()
        
        # Metadata
        self._metric_metadata: Dict[str, Dict[str, Any]] = {}
        self._last_update: Dict[str, float] = {}
    
    def increment_counter(self, name: str, value: float = 1.0, 
                         labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Increment value (default 1.0)
            labels: Optional metric labels
        """
        metric_key = self._create_metric_key(name, labels)
        
        with self._counters_lock:
            self._counters[metric_key] += value
            self._last_update[metric_key] = time.time()
        
        self._update_metadata(metric_key, 'counter', labels)
    
    def set_gauge(self, name: str, value: float, 
                  labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric value.
        
        Args:
            name: Gauge name
            value: Gauge value
            labels: Optional metric labels
        """
        metric_key = self._create_metric_key(name, labels)
        
        with self._gauges_lock:
            self._gauges[metric_key] = value
            self._last_update[metric_key] = time.time()
        
        self._update_metadata(metric_key, 'gauge', labels)
    
    def record_histogram(self, name: str, value: float, 
                        labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a value in a histogram metric.
        
        Args:
            name: Histogram name
            value: Value to record
            labels: Optional metric labels
        """
        metric_key = self._create_metric_key(name, labels)
        
        with self._histograms_lock:
            self._histograms[metric_key].append(value)
            self._last_update[metric_key] = time.time()
            
            # Update statistics
            values = list(self._histograms[metric_key])
            if values:
                self._histogram_stats[metric_key] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': statistics.mean(values),
                    'median': statistics.median(values),
                    'stddev': statistics.stdev(values) if len(values) > 1 else 0
                }
        
        self._update_metadata(metric_key, 'histogram', labels)
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        Get counter value.
        
        Args:
            name: Counter name
            labels: Optional metric labels
            
        Returns:
            Counter value
        """
        metric_key = self._create_metric_key(name, labels)
        
        with self._counters_lock:
            return self._counters.get(metric_key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        Get gauge value.
        
        Args:
            name: Gauge name
            labels: Optional metric labels
            
        Returns:
            Gauge value
        """
        metric_key = self._create_metric_key(name, labels)
        
        with self._gauges_lock:
            return self._gauges.get(metric_key, 0.0)
    
    def get_histogram_stats(self, name: str, 
                           labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Get histogram statistics.
        
        Args:
            name: Histogram name
            labels: Optional metric labels
            
        Returns:
            Histogram statistics
        """
        metric_key = self._create_metric_key(name, labels)
        
        with self._histograms_lock:
            return self._histogram_stats.get(metric_key, {
                'count': 0,
                'min': 0,
                'max': 0,
                'avg': 0,
                'median': 0,
                'stddev': 0
            }).copy()
    
    def get_histogram_percentiles(self, name: str, percentiles: List[float],
                                 labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Get histogram percentiles.
        
        Args:
            name: Histogram name
            percentiles: List of percentiles (0-100)
            labels: Optional metric labels
            
        Returns:
            Percentile values
        """
        metric_key = self._create_metric_key(name, labels)
        
        with self._histograms_lock:
            values = list(self._histograms.get(metric_key, []))
            
            if not values:
                return {f'p{p}': 0 for p in percentiles}
            
            sorted_values = sorted(values)
            result = {}
            
            for p in percentiles:
                if p == 0:
                    result[f'p{p}'] = sorted_values[0]
                elif p == 100:
                    result[f'p{p}'] = sorted_values[-1]
                else:
                    index = int((p / 100) * (len(sorted_values) - 1))
                    result[f'p{p}'] = sorted_values[index]
            
            return result
    
    def reset_metric(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Reset a metric to zero/empty.
        
        Args:
            name: Metric name
            labels: Optional metric labels
        """
        metric_key = self._create_metric_key(name, labels)
        
        with self._counters_lock:
            if metric_key in self._counters:
                self._counters[metric_key] = 0.0
        
        with self._gauges_lock:
            if metric_key in self._gauges:
                self._gauges[metric_key] = 0.0
        
        with self._histograms_lock:
            if metric_key in self._histograms:
                self._histograms[metric_key].clear()
                self._histogram_stats[metric_key] = {
                    'count': 0, 'min': 0, 'max': 0, 'avg': 0, 'median': 0, 'stddev': 0
                }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics as a snapshot.
        
        Returns:
            All metrics organized by type
        """
        with self._counters_lock:
            counters = self._counters.copy()
        
        with self._gauges_lock:
            gauges = self._gauges.copy()
        
        with self._histograms_lock:
            histogram_stats = self._histogram_stats.copy()
        
        return {
            'counters': counters,
            'gauges': gauges,
            'histograms': histogram_stats,
            'metadata': self._metric_metadata.copy(),
            'last_update': self._last_update.copy()
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary for monitoring.
        
        Returns:
            High-level metrics summary
        """
        with self._counters_lock:
            total_counters = len(self._counters)
            top_counters = sorted(
                [(k, v) for k, v in self._counters.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        
        with self._gauges_lock:
            total_gauges = len(self._gauges)
            recent_gauges = [
                (k, v) for k, v in self._gauges.items()
                if self._last_update.get(k, 0) > time.time() - 300  # Last 5 minutes
            ]
        
        with self._histograms_lock:
            total_histograms = len(self._histograms)
            active_histograms = [
                k for k in self._histograms.keys()
                if self._last_update.get(k, 0) > time.time() - 300
            ]
        
        return {
            'total_metrics': total_counters + total_gauges + total_histograms,
            'counters': {
                'count': total_counters,
                'top_values': top_counters
            },
            'gauges': {
                'count': total_gauges,
                'recent_count': len(recent_gauges)
            },
            'histograms': {
                'count': total_histograms,
                'active_count': len(active_histograms)
            }
        }
    
    def export_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics
        """
        lines = []
        
        # Export counters
        with self._counters_lock:
            for metric_key, value in self._counters.items():
                name, labels = self._parse_metric_key(metric_key)
                label_str = self._format_prometheus_labels(labels)
                lines.append(f'# TYPE {name} counter')
                lines.append(f'{name}{label_str} {value}')
        
        # Export gauges
        with self._gauges_lock:
            for metric_key, value in self._gauges.items():
                name, labels = self._parse_metric_key(metric_key)
                label_str = self._format_prometheus_labels(labels)
                lines.append(f'# TYPE {name} gauge')
                lines.append(f'{name}{label_str} {value}')
        
        # Export histograms
        with self._histograms_lock:
            for metric_key, stats in self._histogram_stats.items():
                name, labels = self._parse_metric_key(metric_key)
                label_str = self._format_prometheus_labels(labels)
                
                lines.append(f'# TYPE {name} histogram')
                lines.append(f'{name}_count{label_str} {stats["count"]}')
                lines.append(f'{name}_sum{label_str} {stats["avg"] * stats["count"]}')
                
                # Add quantiles
                percentiles = self.get_histogram_percentiles(name.split('|')[0], [50, 90, 95, 99], labels)
                for percentile, value in percentiles.items():
                    quantile = float(percentile[1:]) / 100
                    quantile_labels = dict(labels) if labels else {}
                    quantile_labels['quantile'] = str(quantile)
                    quantile_label_str = self._format_prometheus_labels(quantile_labels)
                    lines.append(f'{name}{quantile_label_str} {value}')
        
        return '\n'.join(lines)
    
    def _create_metric_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create unique metric key including labels."""
        if not labels:
            return name
        
        label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
        return f'{name}|{label_str}'
    
    def _parse_metric_key(self, metric_key: str) -> tuple:
        """Parse metric key back to name and labels."""
        if '|' not in metric_key:
            return metric_key, None
        
        name, label_str = metric_key.split('|', 1)
        labels = {}
        
        if label_str:
            for pair in label_str.split(','):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    labels[k] = v
        
        return name, labels if labels else None
    
    def _format_prometheus_labels(self, labels: Optional[Dict[str, str]]) -> str:
        """Format labels for Prometheus export."""
        if not labels:
            return ''
        
        formatted_labels = []
        for key, value in sorted(labels.items()):
            # Escape quotes in values
            escaped_value = value.replace('"', '\\"')
            formatted_labels.append(f'{key}="{escaped_value}"')
        
        return '{' + ','.join(formatted_labels) + '}'
    
    def _update_metadata(self, metric_key: str, metric_type: str, 
                        labels: Optional[Dict[str, str]]) -> None:
        """Update metric metadata."""
        self._metric_metadata[metric_key] = {
            'type': metric_type,
            'labels': labels,
            'created_at': self._metric_metadata.get(metric_key, {}).get('created_at', time.time()),
            'updated_at': time.time()
        }