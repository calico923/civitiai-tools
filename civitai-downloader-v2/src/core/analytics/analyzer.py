#!/usr/bin/env python3
"""
Analytics Analyzer for CivitAI Downloader.
Provides advanced analysis and insights from collected analytics data.
"""

import sqlite3
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import numpy as np
from collections import defaultdict, Counter
import time

try:
    from .collector import AnalyticsCollector, EventType
    from ...core.config.system_config import SystemConfig
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.analytics.collector import AnalyticsCollector, EventType
    from core.config.system_config import SystemConfig


@dataclass
class TimeSeriesData:
    """Time series data point."""
    timestamp: float
    value: float
    label: Optional[str] = None


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trend_direction: str  # "up", "down", "stable"
    significance: str     # "high", "medium", "low"
    
    @property
    def is_improving(self) -> bool:
        """Check if trend is improving (context-dependent)."""
        improving_metrics = ['success_rate', 'download_speed', 'safe_files']
        declining_metrics = ['failure_rate', 'error_count', 'scan_time']
        
        if any(metric in self.metric_name.lower() for metric in improving_metrics):
            return self.trend_direction == "up"
        elif any(metric in self.metric_name.lower() for metric in declining_metrics):
            return self.trend_direction == "down"
        else:
            return self.trend_direction == "stable"


@dataclass
class UsagePattern:
    """Usage pattern analysis."""
    pattern_type: str
    description: str
    frequency: int
    confidence: float
    examples: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PerformanceInsight:
    """Performance insight analysis."""
    category: str
    metric: str
    current_value: float
    benchmark_value: float
    impact: str  # "positive", "negative", "neutral"
    severity: str  # "critical", "warning", "info"
    recommendation: str
    estimated_improvement: Optional[float] = None


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report."""
    report_id: str
    generated_at: float
    time_period: Tuple[float, float]
    summary: Dict[str, Any]
    trends: List[TrendAnalysis]
    patterns: List[UsagePattern]
    insights: List[PerformanceInsight]
    recommendations: List[str]
    charts_data: Dict[str, List[TimeSeriesData]] = field(default_factory=dict)


class AnalyticsAnalyzer:
    """Advanced analytics analyzer."""
    
    def __init__(self, collector: AnalyticsCollector, config: Optional[SystemConfig] = None):
        """
        Initialize analytics analyzer.
        
        Args:
            collector: Analytics collector instance
            config: System configuration
        """
        self.collector = collector
        self.config = config or SystemConfig()
        self.db_path = collector.db_path
        
        # Analysis configuration
        self.trend_significance_threshold = self.config.get('analytics.trend_threshold', 5.0)  # %
        self.pattern_confidence_threshold = self.config.get('analytics.pattern_threshold', 0.7)
        self.performance_benchmark = {
            'download_speed': 5 * 1024 * 1024,  # 5 MB/s
            'success_rate': 95.0,               # 95%
            'scan_time': 1.0,                   # 1 second
            'cpu_usage': 70.0,                  # 70%
            'memory_usage': 60.0                # 60%
        }
    
    def generate_report(self, start_time: Optional[float] = None,
                       end_time: Optional[float] = None,
                       period_days: int = 7) -> AnalyticsReport:
        """
        Generate comprehensive analytics report.
        
        Args:
            start_time: Start timestamp (defaults to period_days ago)
            end_time: End timestamp (defaults to now)
            period_days: Period length in days
            
        Returns:
            Analytics report
        """
        if end_time is None:
            end_time = time.time()
        if start_time is None:
            start_time = end_time - (period_days * 24 * 3600)
        
        report_id = f"report_{int(time.time())}"
        
        # Generate analysis components
        summary = self._generate_summary(start_time, end_time)
        trends = self._analyze_trends(start_time, end_time)
        patterns = self._identify_patterns(start_time, end_time)
        insights = self._generate_insights(start_time, end_time)
        recommendations = self._generate_recommendations(trends, patterns, insights)
        charts_data = self._prepare_charts_data(start_time, end_time)
        
        return AnalyticsReport(
            report_id=report_id,
            generated_at=time.time(),
            time_period=(start_time, end_time),
            summary=summary,
            trends=trends,
            patterns=patterns,
            insights=insights,
            recommendations=recommendations,
            charts_data=charts_data
        )
    
    def _generate_summary(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Generate summary statistics for the period."""
        summary = {
            'period': {
                'start': datetime.fromtimestamp(start_time).isoformat(),
                'end': datetime.fromtimestamp(end_time).isoformat(),
                'duration_hours': (end_time - start_time) / 3600
            },
            'downloads': self._summarize_downloads(start_time, end_time),
            'searches': self._summarize_searches(start_time, end_time),
            'security': self._summarize_security(start_time, end_time),
            'performance': self._summarize_performance(start_time, end_time),
            'errors': self._summarize_errors(start_time, end_time)
        }
        
        return summary
    
    def _summarize_downloads(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Summarize download activity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total downloads
            total_downloads = conn.execute("""
                SELECT COUNT(*) as count FROM events 
                WHERE event_type = 'download_started' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()['count']
            
            # Successful downloads
            successful = conn.execute("""
                SELECT COUNT(*) as count FROM events 
                WHERE event_type = 'download_completed' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()['count']
            
            # Failed downloads
            failed = conn.execute("""
                SELECT COUNT(*) as count FROM events 
                WHERE event_type = 'download_failed' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()['count']
            
            # Total bytes downloaded
            bytes_result = conn.execute("""
                SELECT SUM(CAST(JSON_EXTRACT(data, '$.file_size') AS INTEGER)) as total_bytes
                FROM events 
                WHERE event_type = 'download_completed' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            total_bytes = bytes_result['total_bytes'] or 0
            
            # Average download speed
            speed_result = conn.execute("""
                SELECT AVG(CAST(JSON_EXTRACT(data, '$.download_speed') AS REAL)) as avg_speed
                FROM events 
                WHERE event_type = 'download_completed' 
                AND timestamp BETWEEN ? AND ?
                AND JSON_EXTRACT(data, '$.download_speed') IS NOT NULL
            """, (start_time, end_time)).fetchone()
            
            avg_speed = speed_result['avg_speed'] or 0
            
            return {
                'total_downloads': total_downloads,
                'successful_downloads': successful,
                'failed_downloads': failed,
                'success_rate': (successful / total_downloads * 100) if total_downloads > 0 else 0,
                'total_bytes_downloaded': total_bytes,
                'total_size_gb': total_bytes / (1024**3),
                'average_download_speed_mbps': avg_speed / (1024**2),
                'unique_models': self._count_unique_models(start_time, end_time)
            }
    
    def _summarize_searches(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Summarize search activity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total searches
            total_searches = conn.execute("""
                SELECT COUNT(*) as count FROM events 
                WHERE event_type = 'search_performed' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()['count']
            
            # Average results per search
            avg_results = conn.execute("""
                SELECT AVG(CAST(JSON_EXTRACT(data, '$.result_count') AS REAL)) as avg_results
                FROM events 
                WHERE event_type = 'search_performed' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            avg_results_count = avg_results['avg_results'] or 0
            
            # Average response time
            avg_response = conn.execute("""
                SELECT AVG(CAST(JSON_EXTRACT(data, '$.response_time') AS REAL)) as avg_time
                FROM events 
                WHERE event_type = 'search_performed' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            avg_response_time = avg_response['avg_time'] or 0
            
            return {
                'total_searches': total_searches,
                'average_results_per_search': avg_results_count,
                'average_response_time': avg_response_time,
                'popular_queries': self._get_popular_queries(start_time, end_time)
            }
    
    def _summarize_security(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Summarize security scan activity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Security scan counts by result
            scan_results = conn.execute("""
                SELECT JSON_EXTRACT(data, '$.scan_result') as result, COUNT(*) as count
                FROM events 
                WHERE event_type = 'security_scan' 
                AND timestamp BETWEEN ? AND ?
                GROUP BY JSON_EXTRACT(data, '$.scan_result')
            """, (start_time, end_time)).fetchall()
            
            results_dict = {row['result']: row['count'] for row in scan_results}
            total_scans = sum(results_dict.values())
            
            # Average scan time
            avg_scan_time = conn.execute("""
                SELECT AVG(CAST(JSON_EXTRACT(data, '$.scan_duration') AS REAL)) as avg_time
                FROM events 
                WHERE event_type = 'security_scan' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            return {
                'total_scans': total_scans,
                'safe_files': results_dict.get('safe', 0),
                'suspicious_files': results_dict.get('suspicious', 0),
                'malicious_files': results_dict.get('malicious', 0),
                'threat_detection_rate': ((results_dict.get('suspicious', 0) + 
                                         results_dict.get('malicious', 0)) / total_scans * 100) if total_scans > 0 else 0,
                'average_scan_time': avg_scan_time['avg_time'] or 0
            }
    
    def _summarize_performance(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Summarize performance metrics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Average performance metrics
            perf_stats = conn.execute("""
                SELECT 
                    AVG(cpu_usage) as avg_cpu,
                    AVG(memory_usage) as avg_memory,
                    AVG(download_speed) as avg_speed,
                    AVG(active_connections) as avg_connections
                FROM performance_history 
                WHERE timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            # Network condition distribution
            network_stats = conn.execute("""
                SELECT network_condition, COUNT(*) as count
                FROM performance_history 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY network_condition
            """, (start_time, end_time)).fetchall()
            
            network_dist = {row['network_condition']: row['count'] for row in network_stats}
            
            return {
                'average_cpu_usage': perf_stats['avg_cpu'] or 0,
                'average_memory_usage': perf_stats['avg_memory'] or 0,
                'average_download_speed': perf_stats['avg_speed'] or 0,
                'average_connections': perf_stats['avg_connections'] or 0,
                'network_condition_distribution': network_dist
            }
    
    def _summarize_errors(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Summarize error occurrences."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total errors
            total_errors = conn.execute("""
                SELECT COUNT(*) as count FROM events 
                WHERE event_type = 'error_occurred' 
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()['count']
            
            # Error types
            error_types = conn.execute("""
                SELECT JSON_EXTRACT(data, '$.error_type') as error_type, COUNT(*) as count
                FROM events 
                WHERE event_type = 'error_occurred' 
                AND timestamp BETWEEN ? AND ?
                GROUP BY JSON_EXTRACT(data, '$.error_type')
                ORDER BY count DESC
                LIMIT 10
            """, (start_time, end_time)).fetchall()
            
            return {
                'total_errors': total_errors,
                'error_types': [(row['error_type'], row['count']) for row in error_types]
            }
    
    def _analyze_trends(self, start_time: float, end_time: float) -> List[TrendAnalysis]:
        """Analyze trends over time."""
        trends = []
        
        # Split period into two halves for comparison
        mid_time = start_time + (end_time - start_time) / 2
        
        # Analyze download success rate trend
        first_half_success = self._calculate_success_rate(start_time, mid_time)
        second_half_success = self._calculate_success_rate(mid_time, end_time)
        
        if first_half_success is not None and second_half_success is not None:
            change = ((second_half_success - first_half_success) / first_half_success * 100) if first_half_success > 0 else 0
            trends.append(self._create_trend_analysis(
                "download_success_rate", second_half_success, first_half_success, change
            ))
        
        # Analyze download speed trend
        first_half_speed = self._calculate_avg_download_speed(start_time, mid_time)
        second_half_speed = self._calculate_avg_download_speed(mid_time, end_time)
        
        if first_half_speed is not None and second_half_speed is not None:
            change = ((second_half_speed - first_half_speed) / first_half_speed * 100) if first_half_speed > 0 else 0
            trends.append(self._create_trend_analysis(
                "download_speed", second_half_speed, first_half_speed, change
            ))
        
        # Analyze error rate trend
        first_half_errors = self._calculate_error_rate(start_time, mid_time)
        second_half_errors = self._calculate_error_rate(mid_time, end_time)
        
        if first_half_errors is not None and second_half_errors is not None:
            change = ((second_half_errors - first_half_errors) / first_half_errors * 100) if first_half_errors > 0 else 0
            trends.append(self._create_trend_analysis(
                "error_rate", second_half_errors, first_half_errors, change
            ))
        
        return trends
    
    def _identify_patterns(self, start_time: float, end_time: float) -> List[UsagePattern]:
        """Identify usage patterns."""
        patterns = []
        
        # Peak usage hours
        hourly_activity = self._analyze_hourly_activity(start_time, end_time)
        if hourly_activity:
            peak_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3]
            patterns.append(UsagePattern(
                pattern_type="peak_hours",
                description=f"Peak activity hours: {', '.join([f'{h}:00' for h, _ in peak_hours])}",
                frequency=sum(count for _, count in peak_hours),
                confidence=0.8,
                recommendations=["Schedule maintenance during low-activity hours"]
            ))
        
        # Batch download patterns
        bulk_patterns = self._analyze_bulk_patterns(start_time, end_time)
        if bulk_patterns:
            patterns.extend(bulk_patterns)
        
        # Search patterns
        search_patterns = self._analyze_search_patterns(start_time, end_time)
        if search_patterns:
            patterns.extend(search_patterns)
        
        return patterns
    
    def _generate_insights(self, start_time: float, end_time: float) -> List[PerformanceInsight]:
        """Generate performance insights."""
        insights = []
        
        # Download performance insights
        avg_speed = self._calculate_avg_download_speed(start_time, end_time)
        if avg_speed is not None:
            benchmark_speed = self.performance_benchmark['download_speed']
            if avg_speed < benchmark_speed * 0.8:  # 20% below benchmark
                insights.append(PerformanceInsight(
                    category="performance",
                    metric="download_speed",
                    current_value=avg_speed,
                    benchmark_value=benchmark_speed,
                    impact="negative",
                    severity="warning",
                    recommendation="Consider optimizing network settings or checking connection quality",
                    estimated_improvement=(benchmark_speed - avg_speed) / avg_speed * 100
                ))
        
        # Success rate insights
        success_rate = self._calculate_success_rate(start_time, end_time)
        if success_rate is not None:
            benchmark_rate = self.performance_benchmark['success_rate']
            if success_rate < benchmark_rate:
                insights.append(PerformanceInsight(
                    category="reliability",
                    metric="success_rate",
                    current_value=success_rate,
                    benchmark_value=benchmark_rate,
                    impact="negative",
                    severity="critical" if success_rate < 80 else "warning",
                    recommendation="Investigate download failures and improve error handling"
                ))
        
        # Resource usage insights
        avg_cpu, avg_memory = self._calculate_avg_resource_usage(start_time, end_time)
        if avg_cpu is not None and avg_cpu > self.performance_benchmark['cpu_usage']:
            insights.append(PerformanceInsight(
                category="resources",
                metric="cpu_usage",
                current_value=avg_cpu,
                benchmark_value=self.performance_benchmark['cpu_usage'],
                impact="negative",
                severity="warning",
                recommendation="Consider reducing concurrent downloads or optimizing processing"
            ))
        
        return insights
    
    def _generate_recommendations(self, trends: List[TrendAnalysis], 
                                patterns: List[UsagePattern],
                                insights: List[PerformanceInsight]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Trend-based recommendations
        for trend in trends:
            if not trend.is_improving and trend.significance == "high":
                if "success_rate" in trend.metric_name:
                    recommendations.append("Investigate and address download failure causes")
                elif "speed" in trend.metric_name:
                    recommendations.append("Optimize network configuration for better performance")
                elif "error" in trend.metric_name:
                    recommendations.append("Implement better error handling and retry mechanisms")
        
        # Pattern-based recommendations
        for pattern in patterns:
            recommendations.extend(pattern.recommendations)
        
        # Insight-based recommendations
        critical_insights = [i for i in insights if i.severity == "critical"]
        if critical_insights:
            recommendations.append("Address critical performance issues immediately")
        
        # General recommendations
        if len(insights) > 3:
            recommendations.append("Consider comprehensive performance optimization")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _prepare_charts_data(self, start_time: float, end_time: float) -> Dict[str, List[TimeSeriesData]]:
        """Prepare time series data for charts."""
        charts = {}
        
        # Download activity over time
        charts['download_activity'] = self._get_download_activity_timeseries(start_time, end_time)
        
        # Performance metrics over time
        charts['performance_metrics'] = self._get_performance_timeseries(start_time, end_time)
        
        # Success rate over time
        charts['success_rate'] = self._get_success_rate_timeseries(start_time, end_time)
        
        return charts
    
    # Helper methods
    def _create_trend_analysis(self, metric_name: str, current: float, 
                             previous: float, change_percent: float) -> TrendAnalysis:
        """Create trend analysis object."""
        direction = "up" if change_percent > 0 else "down" if change_percent < 0 else "stable"
        significance = "high" if abs(change_percent) > self.trend_significance_threshold else "medium" if abs(change_percent) > 2 else "low"
        
        return TrendAnalysis(
            metric_name=metric_name,
            current_value=current,
            previous_value=previous,
            change_percent=change_percent,
            trend_direction=direction,
            significance=significance
        )
    
    def _calculate_success_rate(self, start_time: float, end_time: float) -> Optional[float]:
        """Calculate download success rate for period."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT 
                    SUM(CASE WHEN event_type = 'download_completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN event_type = 'download_started' THEN 1 ELSE 0 END) as started
                FROM events 
                WHERE event_type IN ('download_started', 'download_completed')
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            completed = result[0] or 0
            started = result[1] or 0
            
            if started > 0:
                return (completed / started) * 100
            return None
    
    def _calculate_avg_download_speed(self, start_time: float, end_time: float) -> Optional[float]:
        """Calculate average download speed for period."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT AVG(CAST(JSON_EXTRACT(data, '$.download_speed') AS REAL)) as avg_speed
                FROM events 
                WHERE event_type = 'download_completed'
                AND timestamp BETWEEN ? AND ?
                AND JSON_EXTRACT(data, '$.download_speed') IS NOT NULL
            """, (start_time, end_time)).fetchone()
            
            return result[0] if result[0] is not None else None
    
    def _calculate_error_rate(self, start_time: float, end_time: float) -> Optional[float]:
        """Calculate error rate for period."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT 
                    SUM(CASE WHEN event_type = 'error_occurred' THEN 1 ELSE 0 END) as errors,
                    COUNT(*) as total
                FROM events 
                WHERE timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            errors = result[0] or 0
            total = result[1] or 0
            
            if total > 0:
                return (errors / total) * 100
            return None
    
    def _calculate_avg_resource_usage(self, start_time: float, end_time: float) -> Tuple[Optional[float], Optional[float]]:
        """Calculate average CPU and memory usage."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT AVG(cpu_usage), AVG(memory_usage)
                FROM performance_history 
                WHERE timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            return result[0], result[1]
    
    def _count_unique_models(self, start_time: float, end_time: float) -> int:
        """Count unique models downloaded."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COUNT(DISTINCT JSON_EXTRACT(data, '$.model_metadata.model_id')) as unique_models
                FROM events 
                WHERE event_type = 'download_completed'
                AND timestamp BETWEEN ? AND ?
                AND JSON_EXTRACT(data, '$.model_metadata.model_id') IS NOT NULL
            """, (start_time, end_time)).fetchone()
            
            return result[0] or 0
    
    def _get_popular_queries(self, start_time: float, end_time: float) -> List[Tuple[str, int]]:
        """Get popular search queries."""
        with sqlite3.connect(self.db_path) as conn:
            results = conn.execute("""
                SELECT JSON_EXTRACT(data, '$.query') as query, COUNT(*) as count
                FROM events 
                WHERE event_type = 'search_performed'
                AND timestamp BETWEEN ? AND ?
                AND JSON_EXTRACT(data, '$.query') IS NOT NULL
                GROUP BY JSON_EXTRACT(data, '$.query')
                ORDER BY count DESC
                LIMIT 10
            """, (start_time, end_time)).fetchall()
            
            return [(row[0], row[1]) for row in results]
    
    def _analyze_hourly_activity(self, start_time: float, end_time: float) -> Dict[int, int]:
        """Analyze activity by hour of day."""
        with sqlite3.connect(self.db_path) as conn:
            results = conn.execute("""
                SELECT 
                    CAST(strftime('%H', datetime(timestamp, 'unixepoch')) AS INTEGER) as hour,
                    COUNT(*) as count
                FROM events 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY hour
            """, (start_time, end_time)).fetchall()
            
            return {row[0]: row[1] for row in results}
    
    def _analyze_bulk_patterns(self, start_time: float, end_time: float) -> List[UsagePattern]:
        """Analyze bulk download patterns."""
        patterns = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Average bulk job size
            avg_size = conn.execute("""
                SELECT AVG(CAST(JSON_EXTRACT(data, '$.total_files') AS INTEGER)) as avg_size
                FROM events 
                WHERE event_type = 'bulk_job_created'
                AND timestamp BETWEEN ? AND ?
            """, (start_time, end_time)).fetchone()
            
            if avg_size[0] is not None and avg_size[0] > 10:
                patterns.append(UsagePattern(
                    pattern_type="large_bulk_jobs",
                    description=f"Average bulk job size: {avg_size[0]:.1f} files",
                    frequency=1,
                    confidence=0.9,
                    recommendations=["Consider optimizing batch sizes for better performance"]
                ))
        
        return patterns
    
    def _analyze_search_patterns(self, start_time: float, end_time: float) -> List[UsagePattern]:
        """Analyze search patterns."""
        patterns = []
        
        popular_queries = self._get_popular_queries(start_time, end_time)
        if popular_queries and len(popular_queries) >= 3:
            top_query = popular_queries[0]
            patterns.append(UsagePattern(
                pattern_type="popular_search",
                description=f"Most popular search: '{top_query[0]}' ({top_query[1]} times)",
                frequency=top_query[1],
                confidence=0.8,
                recommendations=["Consider caching popular search results"]
            ))
        
        return patterns
    
    def _get_download_activity_timeseries(self, start_time: float, end_time: float) -> List[TimeSeriesData]:
        """Get download activity time series."""
        time_series = []
        
        # Divide period into hourly buckets
        current_time = start_time
        hour_seconds = 3600
        
        with sqlite3.connect(self.db_path) as conn:
            while current_time < end_time:
                next_time = min(current_time + hour_seconds, end_time)
                
                count = conn.execute("""
                    SELECT COUNT(*) FROM events 
                    WHERE event_type = 'download_started'
                    AND timestamp BETWEEN ? AND ?
                """, (current_time, next_time)).fetchone()[0]
                
                time_series.append(TimeSeriesData(
                    timestamp=current_time,
                    value=float(count),
                    label=datetime.fromtimestamp(current_time).strftime('%H:%M')
                ))
                
                current_time = next_time
        
        return time_series
    
    def _get_performance_timeseries(self, start_time: float, end_time: float) -> List[TimeSeriesData]:
        """Get performance metrics time series."""
        time_series = []
        
        with sqlite3.connect(self.db_path) as conn:
            results = conn.execute("""
                SELECT timestamp, cpu_usage, memory_usage, download_speed
                FROM performance_history 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            """, (start_time, end_time)).fetchall()
            
            for row in results:
                time_series.append(TimeSeriesData(
                    timestamp=row[0],
                    value=row[1],  # CPU usage
                    label="CPU"
                ))
        
        return time_series
    
    def _get_success_rate_timeseries(self, start_time: float, end_time: float) -> List[TimeSeriesData]:
        """Get success rate time series."""
        time_series = []
        
        # Calculate success rate in hourly windows
        current_time = start_time
        hour_seconds = 3600
        
        while current_time < end_time:
            next_time = min(current_time + hour_seconds, end_time)
            success_rate = self._calculate_success_rate(current_time, next_time)
            
            if success_rate is not None:
                time_series.append(TimeSeriesData(
                    timestamp=current_time,
                    value=success_rate,
                    label=datetime.fromtimestamp(current_time).strftime('%H:%M')
                ))
            
            current_time = next_time
        
        return time_series


if __name__ == "__main__":
    # Test analytics analyzer
    print("Testing Analytics Analyzer...")
    
    from core.analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector()
    analyzer = AnalyticsAnalyzer(collector)
    
    # Generate a test report
    end_time = time.time()
    start_time = end_time - (7 * 24 * 3600)  # 7 days
    
    report = analyzer.generate_report(start_time, end_time)
    
    print(f"Report ID: {report.report_id}")
    print(f"Period: {report.time_period}")
    print(f"Trends: {len(report.trends)}")
    print(f"Patterns: {len(report.patterns)}")
    print(f"Insights: {len(report.insights)}")
    print(f"Recommendations: {len(report.recommendations)}")
    
    collector.stop()
    print("Analytics Analyzer test completed.")