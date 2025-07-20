#!/usr/bin/env python3
"""
Analytics and Reporting System for CivitAI Downloader.

This module provides comprehensive analytics collection, analysis, and reporting
capabilities for monitoring download activities, performance metrics, and usage patterns.
"""

from .collector import (
    AnalyticsCollector,
    EventType,
    AnalyticsEvent,
    DownloadMetrics,
    SearchMetrics,
    SecurityMetrics,
    PerformanceSnapshot,
    get_analytics_collector,
    setup_analytics_collector
)

from .analyzer import (
    AnalyticsAnalyzer,
    TrendAnalysis,
    UsagePattern,
    PerformanceInsight,
    AnalyticsReport,
    TimeSeriesData
)

from .reporter import (
    ReportGenerator,
    ReportConfig,
    create_analytics_dashboard
)

__all__ = [
    # Collector classes and functions
    'AnalyticsCollector',
    'EventType',
    'AnalyticsEvent',
    'DownloadMetrics',
    'SearchMetrics',
    'SecurityMetrics', 
    'PerformanceSnapshot',
    'get_analytics_collector',
    'setup_analytics_collector',
    
    # Analyzer classes
    'AnalyticsAnalyzer',
    'TrendAnalysis',
    'UsagePattern',
    'PerformanceInsight',
    'AnalyticsReport',
    'TimeSeriesData',
    
    # Reporter classes and functions
    'ReportGenerator',
    'ReportConfig',
    'create_analytics_dashboard'
]


def create_complete_analytics_system(config=None, db_path=None):
    """
    Create a complete analytics system with collector, analyzer, and reporter.
    
    Args:
        config: System configuration
        db_path: Path to analytics database
        
    Returns:
        Tuple of (collector, analyzer, generator)
    """
    collector = setup_analytics_collector(config, db_path)
    analyzer = AnalyticsAnalyzer(collector, config)
    generator = ReportGenerator(analyzer, config)
    
    return collector, analyzer, generator


def quick_analytics_report(period_days=7, output_format="html"):
    """
    Generate a quick analytics report for the specified period.
    
    Args:
        period_days: Number of days to include in report
        output_format: Report format ("html", "json", "pdf")
        
    Returns:
        Path to generated report
    """
    import time
    from pathlib import Path
    
    # Create analytics system
    collector, analyzer, generator = create_complete_analytics_system()
    
    try:
        # Generate report for specified period
        end_time = time.time()
        start_time = end_time - (period_days * 24 * 3600)
        
        report = analyzer.generate_report(start_time, end_time)
        
        # Generate report file
        config = ReportConfig(format=output_format)
        output_path = generator.generate_report(report, config)
        
        return output_path
    
    finally:
        # Clean up
        collector.stop()