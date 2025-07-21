#!/usr/bin/env python3
"""
Analytics data analysis system.
Implements requirement 13.4: Statistics analysis, performance metrics.
"""

import sqlite3
import statistics
import time
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter

from .collector import AnalyticsCollector, EventType


@dataclass
class AnalysisReport:
    """Analytics analysis report."""
    period_start: float
    period_end: float
    summary: Dict[str, Any]
    api_statistics: Dict[str, Any]
    download_statistics: Dict[str, Any]
    search_statistics: Dict[str, Any]
    cache_statistics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    error_analysis: Dict[str, Any]
    recommendations: List[str]


class AnalyticsAnalyzer:
    """
    Analytics data analyzer.
    Provides comprehensive analysis and insights per requirement 13.
    """
    
    def __init__(self, collector: AnalyticsCollector):
        """Initialize analytics analyzer."""
        self.collector = collector
    
    def generate_report(self, start_time: float, end_time: float) -> AnalysisReport:
        """Generate comprehensive analytics report."""
        # Get events for the time period
        events = self.collector.get_events(
            start_time=start_time,
            end_time=end_time
        )
        
        # Analyze different aspects
        summary = self._analyze_summary(events, start_time, end_time)
        api_stats = self._analyze_api_statistics(events)
        download_stats = self._analyze_download_statistics(events)
        search_stats = self._analyze_search_statistics(events)
        cache_stats = self._analyze_cache_statistics(events)
        performance = self._analyze_performance_metrics(events)
        errors = self._analyze_error_patterns(events)
        recommendations = self._generate_recommendations(
            api_stats, download_stats, cache_stats, performance, errors
        )
        
        return AnalysisReport(
            period_start=start_time,
            period_end=end_time,
            summary=summary,
            api_statistics=api_stats,
            download_statistics=download_stats,
            search_statistics=search_stats,
            cache_statistics=cache_stats,
            performance_metrics=performance,
            error_analysis=errors,
            recommendations=recommendations
        )
    
    def _analyze_summary(self, events: List[Dict[str, Any]], 
                        start_time: float, end_time: float) -> Dict[str, Any]:
        """Analyze overall summary statistics."""
        duration_hours = (end_time - start_time) / 3600
        
        event_counts = Counter(event['event_type'] for event in events)
        
        # Count unique sessions
        sessions = set(event.get('session_id') for event in events if event.get('session_id'))
        
        return {
            'analysis_period': {
                'start_time': start_time,
                'end_time': end_time,
                'duration_hours': round(duration_hours, 2)
            },
            'total_events': len(events),
            'unique_sessions': len(sessions),
            'events_per_hour': round(len(events) / duration_hours, 2) if duration_hours > 0 else 0,
            'event_type_breakdown': dict(event_counts),
            'most_active_session': self._get_most_active_session(events)
        }
    
    def _analyze_api_statistics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze API usage statistics per requirement 13.1."""
        api_requests = [e for e in events if e['event_type'] == 'api_request']
        api_responses = [e for e in events if e['event_type'] == 'api_response']
        api_errors = [e for e in events if e['event_type'] == 'api_error']
        
        # Match requests with responses/errors
        request_dict = {
            event['data'].get('request_id'): event 
            for event in api_requests 
            if event.get('data', {}).get('request_id')
        }
        
        response_times = []
        status_codes = Counter()
        endpoint_stats = defaultdict(lambda: {'count': 0, 'errors': 0, 'avg_time': 0})
        
        # Process successful responses for response time calculation
        for event in api_responses:
            data = event.get('data', {})
            request_id = data.get('request_id')
            
            if request_id in request_dict:
                request = request_dict[request_id]
                endpoint = request['data'].get('endpoint', 'unknown')
                response_time = data.get('response_time', 0)
                
                endpoint_stats[endpoint]['count'] += 1
                
                if response_time > 0:
                    response_times.append(response_time)
                    endpoint_stats[endpoint]['avg_time'] = (
                        endpoint_stats[endpoint]['avg_time'] + response_time
                    ) / 2
        
        # Process errors separately (count but don't include response time in averages)
        for event in api_errors:
            data = event.get('data', {})
            request_id = data.get('request_id')
            
            if request_id in request_dict:
                request = request_dict[request_id]
                endpoint = request['data'].get('endpoint', 'unknown')
                
                endpoint_stats[endpoint]['count'] += 1
                endpoint_stats[endpoint]['errors'] += 1
        
        for event in api_responses:
            status_code = event.get('data', {}).get('status_code')
            if status_code:
                status_codes[status_code] += 1
        
        # Calculate success rate
        total_requests = len(api_requests)
        successful_responses = len([e for e in api_responses 
                                  if e.get('data', {}).get('status_code', 0) < 400])
        success_rate = (successful_responses / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'total_responses': len(api_responses),
            'total_errors': len(api_errors),
            'success_rate': round(success_rate, 2),
            'avg_response_time': round(statistics.mean(response_times), 3) if response_times else 0,
            'median_response_time': round(statistics.median(response_times), 3) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'status_code_distribution': dict(status_codes),
            'endpoint_statistics': dict(endpoint_stats),
            'requests_per_endpoint': {
                endpoint: stats['count'] 
                for endpoint, stats in endpoint_stats.items()
            }
        }
    
    def _analyze_download_statistics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze download statistics per requirement 13.4."""
        downloads_started = [e for e in events if e['event_type'] == 'download_started']
        downloads_completed = [e for e in events if e['event_type'] == 'download_completed']
        downloads_failed = [e for e in events if e['event_type'] == 'download_failed']
        
        total_downloads = len(downloads_started)
        successful_downloads = len(downloads_completed)
        failed_downloads = len(downloads_failed)
        
        success_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0
        
        # Analyze download sizes and speeds
        file_sizes = []
        download_speeds = []
        download_durations = []
        
        for event in downloads_completed:
            data = event.get('data', {})
            if 'bytes_downloaded' in data:
                file_sizes.append(data['bytes_downloaded'])
            if 'average_speed' in data:
                download_speeds.append(data['average_speed'])
            if 'duration' in data:
                download_durations.append(data['duration'])
        
        # File type analysis
        file_types = Counter()
        for event in downloads_started:
            file_name = event.get('data', {}).get('file_name', '')
            if file_name:
                ext = file_name.split('.')[-1].lower()
                file_types[ext] += 1
        
        return {
            'total_downloads': total_downloads,
            'successful_downloads': successful_downloads,
            'failed_downloads': failed_downloads,
            'success_rate': round(success_rate, 2),
            'avg_file_size_mb': round(statistics.mean(file_sizes) / (1024*1024), 2) if file_sizes else 0,
            'total_downloaded_gb': round(sum(file_sizes) / (1024*1024*1024), 2) if file_sizes else 0,
            'avg_download_speed_mbps': round(statistics.mean(download_speeds) / (1024*1024), 2) if download_speeds else 0,
            'avg_download_duration': round(statistics.mean(download_durations), 2) if download_durations else 0,
            'file_type_distribution': dict(file_types),
            'largest_file_mb': round(max(file_sizes) / (1024*1024), 2) if file_sizes else 0
        }
    
    def _analyze_search_statistics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze search operation statistics."""
        searches = [e for e in events if e['event_type'] == 'search_performed']
        
        if not searches:
            return {
                'total_searches': 0,
                'avg_response_time': 0,
                'avg_results_count': 0,
                'total_results_discovered': 0
            }
        
        response_times = []
        results_counts = []
        queries = Counter()
        
        for event in searches:
            data = event.get('data', {})
            
            if 'response_time' in data:
                response_times.append(data['response_time'])
            if 'results_count' in data:
                results_counts.append(data['results_count'])
            if 'query' in data:
                queries[data['query']] += 1
        
        return {
            'total_searches': len(searches),
            'avg_response_time': round(statistics.mean(response_times), 3) if response_times else 0,
            'avg_results_count': round(statistics.mean(results_counts), 1) if results_counts else 0,
            'total_results_discovered': sum(results_counts),
            'most_common_queries': dict(queries.most_common(10)),
            'median_response_time': round(statistics.median(response_times), 3) if response_times else 0
        }
    
    def _analyze_cache_statistics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cache performance per requirement 13.2."""
        cache_hits = [e for e in events if e['event_type'] == 'cache_hit']
        cache_misses = [e for e in events if e['event_type'] == 'cache_miss']
        
        total_cache_requests = len(cache_hits) + len(cache_misses)
        hit_rate = (len(cache_hits) / total_cache_requests * 100) if total_cache_requests > 0 else 0
        
        # Analyze cache ages
        cache_ages = []
        for event in cache_hits:
            age = event.get('data', {}).get('cache_age')
            if age:
                cache_ages.append(age)
        
        return {
            'total_cache_requests': total_cache_requests,
            'cache_hits': len(cache_hits),
            'cache_misses': len(cache_misses),
            'hit_rate_percent': round(hit_rate, 2),
            'avg_cache_age_minutes': round(statistics.mean(cache_ages) / 60, 2) if cache_ages else 0,
            'efficiency_score': round(hit_rate, 1)
        }
    
    def _analyze_performance_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall performance metrics."""
        # Time distribution analysis
        if not events:
            return {'events_per_hour': [], 'peak_hour': None, 'quiet_hour': None}
        
        # Group events by hour
        hourly_counts = defaultdict(int)
        for event in events:
            hour = int(event['timestamp']) // 3600
            hourly_counts[hour] += 1
        
        if hourly_counts:
            peak_hour = max(hourly_counts.items(), key=lambda x: x[1])
            quiet_hour = min(hourly_counts.items(), key=lambda x: x[1])
        else:
            peak_hour = quiet_hour = None
        
        return {
            'events_per_hour': dict(hourly_counts),
            'peak_hour': {'hour': peak_hour[0], 'events': peak_hour[1]} if peak_hour else None,
            'quiet_hour': {'hour': quiet_hour[0], 'events': quiet_hour[1]} if quiet_hour else None,
            'total_active_hours': len(hourly_counts)
        }
    
    def _analyze_error_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze error patterns and frequencies."""
        api_errors = [e for e in events if e['event_type'] == 'api_error']
        download_errors = [e for e in events if e['event_type'] == 'download_failed']
        
        # Categorize API errors
        api_error_types = Counter()
        for event in api_errors:
            error_type = event.get('data', {}).get('error_type', 'unknown')
            api_error_types[error_type] += 1
        
        # Categorize download errors  
        download_error_types = Counter()
        for event in download_errors:
            error_type = event.get('data', {}).get('error_type', 'unknown')
            download_error_types[error_type] += 1
        
        total_errors = len(api_errors) + len(download_errors)
        
        return {
            'total_errors': total_errors,
            'api_errors': len(api_errors),
            'download_errors': len(download_errors),
            'api_error_types': dict(api_error_types),
            'download_error_types': dict(download_error_types),
            'most_common_error': api_error_types.most_common(1)[0][0] if api_error_types else None
        }
    
    def _generate_recommendations(self, api_stats: Dict[str, Any], 
                                 download_stats: Dict[str, Any],
                                 cache_stats: Dict[str, Any],
                                 performance: Dict[str, Any],
                                 errors: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # API recommendations
        if api_stats['success_rate'] < 95:
            recommendations.append(
                f"API success rate is {api_stats['success_rate']}%. Consider implementing retry logic."
            )
        
        if api_stats['avg_response_time'] > 5.0:
            recommendations.append(
                f"Average API response time is {api_stats['avg_response_time']}s. Consider optimizing requests."
            )
        
        # Cache recommendations
        if cache_stats['hit_rate_percent'] < 50:
            recommendations.append(
                f"Cache hit rate is only {cache_stats['hit_rate_percent']}%. Review caching strategy."
            )
        
        # Download recommendations
        if download_stats['success_rate'] < 90:
            recommendations.append(
                f"Download success rate is {download_stats['success_rate']}%. Improve error handling."
            )
        
        if download_stats['avg_download_speed_mbps'] < 1.0:
            recommendations.append(
                "Download speeds are below 1 MB/s. Check network conditions or increase parallelism."
            )
        
        # Error analysis recommendations
        if errors['total_errors'] > 0:
            if errors['most_common_error']:
                recommendations.append(
                    f"Most common error: '{errors['most_common_error']}'. Focus on resolving this issue."
                )
        
        if not recommendations:
            recommendations.append("System performance looks good. Continue monitoring.")
        
        return recommendations
    
    def _get_most_active_session(self, events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get the most active session information."""
        session_counts = Counter(
            event.get('session_id') for event in events 
            if event.get('session_id')
        )
        
        if not session_counts:
            return None
        
        most_active = session_counts.most_common(1)[0]
        return {
            'session_id': most_active[0],
            'event_count': most_active[1]
        }
    
    def get_daily_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get daily summary for the last N days."""
        end_time = time.time()
        start_time = end_time - (days * 24 * 3600)
        
        report = self.generate_report(start_time, end_time)
        
        return {
            'period': f"Last {days} days",
            'summary': report.summary,
            'key_metrics': {
                'api_success_rate': report.api_statistics['success_rate'],
                'download_success_rate': report.download_statistics['success_rate'],
                'cache_hit_rate': report.cache_statistics['hit_rate_percent'],
                'total_downloads': report.download_statistics['total_downloads'],
                'total_data_gb': report.download_statistics['total_downloaded_gb']
            },
            'recommendations': report.recommendations[:3]  # Top 3 recommendations
        }