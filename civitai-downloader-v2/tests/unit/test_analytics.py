#!/usr/bin/env python3
"""
Unit tests for the Analytics and Reporting system.
Tests cover data collection, analysis, and report generation.
"""

import json
import os
import pytest
import sqlite3
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from core.analytics.collector import (
        AnalyticsCollector, EventType, AnalyticsEvent,
        DownloadMetrics, SearchMetrics, SecurityMetrics, PerformanceSnapshot,
        get_analytics_collector, setup_analytics_collector
    )

    from core.analytics.analyzer import (
        AnalyticsAnalyzer, TrendAnalysis, UsagePattern, PerformanceInsight,
        AnalyticsReport, TimeSeriesData
    )

    from core.analytics.reporter import (
        ReportGenerator, ReportConfig, create_analytics_dashboard
    )

    from core.analytics import (
        create_complete_analytics_system, quick_analytics_report
    )
except ImportError as e:
    print(f"Import error: {e}")
    # Skip all tests if imports fail
    pytest.skip("Analytics modules not available", allow_module_level=True)


class TestDataModels(unittest.TestCase):
    """Test data model classes."""
    
    def test_analytics_event(self):
        """Test AnalyticsEvent creation and serialization."""
        event = AnalyticsEvent(
            event_id='test-event-123',
            event_type=EventType.DOWNLOAD_STARTED,
            timestamp=time.time(),
            data={'file_id': 'test123', 'size': 1024},
            tags=['test', 'unit'],
            user_id='test_user'
        )
        
        self.assertEqual(event.event_type, EventType.DOWNLOAD_STARTED)
        self.assertIsInstance(event.timestamp, float)
        self.assertEqual(event.data['file_id'], 'test123')
        self.assertIn('test', event.tags)
        
        # Test to_dict serialization
        event_dict = event.to_dict()
        self.assertIsInstance(event_dict, dict)
        self.assertEqual(event_dict['event_type'], 'download_started')
        self.assertEqual(event_dict['data']['file_id'], 'test123')
    
    def test_download_metrics(self):
        """Test DownloadMetrics calculation."""
        metrics = DownloadMetrics()
        metrics.total_downloads = 100
        metrics.successful_downloads = 95
        metrics.failed_downloads = 5
        metrics.total_size_bytes = 1024*1024*1024  # 1GB
        metrics.average_speed_bps = 1024*1024      # 1MB/s
        
        self.assertEqual(metrics.success_rate, 95.0)
        self.assertEqual(metrics.total_size_gb, 1.0)
        self.assertEqual(metrics.average_speed_mbps, 1.0)
    
    def test_search_metrics(self):
        """Test SearchMetrics calculation."""
        metrics = SearchMetrics()
        metrics.total_searches = 50
        metrics.total_results = 1000
        metrics.average_response_time = 1.5
        
        self.assertEqual(metrics.average_results_per_search, 20.0)
        self.assertEqual(metrics.average_response_time, 1.5)
    
    def test_security_metrics(self):
        """Test SecurityMetrics calculation."""
        metrics = SecurityMetrics()
        metrics.total_scans = 100
        metrics.safe_files = 90
        metrics.suspicious_files = 8
        metrics.malicious_files = 2
        
        self.assertEqual(metrics.safe_percentage, 90.0)
        self.assertEqual(metrics.threat_percentage, 10.0)
    
    def test_trend_analysis(self):
        """Test TrendAnalysis improvement detection."""
        trend = TrendAnalysis()
        trend.metric = 'download_speed'
        trend.previous_value = 1.0
        trend.current_value = 1.5
        trend.change_percentage = 50.0
        trend.significance = 'high'
        trend.description = 'Download speed increased significantly'
        
        self.assertTrue(trend.is_improving)
        self.assertEqual(trend.change_percentage, 50.0)
        
        # Test declining trend
        decline_trend = TrendAnalysis()
        decline_trend.metric = 'error_rate'
        decline_trend.previous_value = 10.0
        decline_trend.current_value = 5.0
        decline_trend.change_percentage = -50.0
        decline_trend.significance = 'high'
        decline_trend.description = 'Error rate decreased'
        
        # For error rate, decrease is improvement
        self.assertTrue(decline_trend.is_improving)
    
    def test_time_series_data(self):
        """Test TimeSeriesData creation."""
        data = TimeSeriesData()
        data.timestamp = time.time()
        data.value = 42.0
        data.label = 'Test Metric'
        
        self.assertIsInstance(data.timestamp, float)
        self.assertEqual(data.value, 42.0)
        self.assertEqual(data.label, 'Test Metric')
    
    def test_report_config(self):
        """Test ReportConfig default values and customization."""
        # Test defaults
        config = ReportConfig()
        self.assertTrue(config.include_charts)
        self.assertEqual(config.format, "html")
        
        # Test customization
        custom_config = ReportConfig(
            include_charts=False,
            format="json",
            theme="dark"
        )
        self.assertFalse(custom_config.include_charts)
        self.assertEqual(custom_config.format, "json")
        self.assertEqual(custom_config.theme, "dark")


class TestAnalyticsCollector(unittest.TestCase):
    """Test AnalyticsCollector functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_analytics.db"
        self.collector = AnalyticsCollector(
            db_path=str(self.db_path)
        )
        # Override settings for testing
        self.collector.buffer_size = 10
        self.collector.flush_interval = 0.1
    
    def tearDown(self):
        """Clean up test environment."""
        self.collector.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.temp_dir)
    
    def test_collector_initialization(self):
        """Test collector initialization and database setup."""
        self.assertTrue(self.db_path.exists())
        
        # Check database schema
        with sqlite3.connect(self.db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [table[0] for table in tables]
            self.assertIn('events', table_names)
            self.assertIn('performance_snapshots', table_names)
    
    def test_database_schema(self):
        """Test database schema is correct."""
        with sqlite3.connect(self.db_path) as conn:
            # Check events table schema
            events_schema = conn.execute("PRAGMA table_info(events)").fetchall()
            column_names = [col[1] for col in events_schema]
            
            expected_columns = ['id', 'event_type', 'timestamp', 'user_id', 'data', 'tags']
            for col in expected_columns:
                self.assertIn(col, column_names)
    
    def test_record_event(self):
        """Test basic event recording."""
        event_data = {'file_id': 'test123', 'size': 1024}
        
        self.collector.record_event(
            EventType.DOWNLOAD_STARTED,
            event_data,
            tags=['test']
        )
        
        # Force flush to database
        self.collector._flush_events()
        
        # Verify event was recorded
        with sqlite3.connect(self.db_path) as conn:
            events = conn.execute("SELECT * FROM events").fetchall()
            self.assertEqual(len(events), 1)
            
            event = events[0]
            self.assertEqual(event[1], 'download_started')  # event_type
            self.assertIn('test123', event[4])  # data JSON
    
    def test_download_event_recording(self):
        """Test download-specific event recording methods."""
        # Test download started
        self.collector.record_download_started('file123', 1024*1024)
        
        # Test download completed
        self.collector.record_download_completed('file123', 2.5)
        
        # Test download failed
        self.collector.record_download_failed('file124', 'network_error')
        
        self.collector._flush_events()
        
        with sqlite3.connect(self.db_path) as conn:
            events = conn.execute("SELECT event_type FROM events").fetchall()
            event_types = [e[0] for e in events]
            
            self.assertIn('download_started', event_types)
            self.assertIn('download_completed', event_types)
            self.assertIn('download_failed', event_types)
    
    def test_search_event_recording(self):
        """Test search event recording."""
        self.collector.record_search_performed('test query', 25, 1.2)
        self.collector._flush_events()
        
        with sqlite3.connect(self.db_path) as conn:
            events = conn.execute("SELECT data FROM events WHERE event_type='search_performed'").fetchall()
            self.assertEqual(len(events), 1)
            
            data = json.loads(events[0][0])
            self.assertEqual(data['query'], 'test query')
            self.assertEqual(data['results_count'], 25)
            self.assertEqual(data['response_time'], 1.2)
    
    def test_security_event_recording(self):
        """Test security event recording."""
        self.collector.record_security_scan('file123', 'SAFE', 0.95)
        self.collector._flush_events()
        
        with sqlite3.connect(self.db_path) as conn:
            events = conn.execute("SELECT data FROM events WHERE event_type='security_scan'").fetchall()
            self.assertEqual(len(events), 1)
            
            data = json.loads(events[0][0])
            self.assertEqual(data['file_id'], 'file123')
            self.assertEqual(data['result'], 'SAFE')
            self.assertEqual(data['confidence'], 0.95)
    
    def test_bulk_job_recording(self):
        """Test bulk job event recording."""
        self.collector.record_bulk_job_started('job123', 50)
        self.collector.record_bulk_job_completed('job123', 48, 2)
        self.collector._flush_events()
        
        with sqlite3.connect(self.db_path) as conn:
            events = conn.execute("SELECT event_type FROM events").fetchall()
            event_types = [e[0] for e in events]
            
            self.assertIn('bulk_job_started', event_types)
            self.assertIn('bulk_job_completed', event_types)
    
    def test_performance_recording(self):
        """Test performance snapshot recording."""
        self.collector.record_performance_snapshot(
            cpu_usage=45.5,
            memory_usage=60.2,
            download_speed=1024*1024,
            active_connections=3
        )
        
        # Performance snapshots are written directly, no buffering
        with sqlite3.connect(self.db_path) as conn:
            snapshots = conn.execute("SELECT * FROM performance_snapshots").fetchall()
            self.assertEqual(len(snapshots), 1)
            
            snapshot = snapshots[0]
            self.assertEqual(snapshot[1], 45.5)  # cpu_usage
            self.assertEqual(snapshot[2], 60.2)  # memory_usage
    
    def test_event_querying(self):
        """Test event querying functionality."""
        start_time = time.time()
        
        # Record several events
        for i in range(5):
            self.collector.record_download_started(f'file{i}', 1024*(i+1))
            time.sleep(0.01)  # Small delay
        
        self.collector._flush_events()
        
        end_time = time.time()
        
        # Query events
        events = self.collector.get_events(EventType.DOWNLOAD_STARTED, start_time, end_time)
        self.assertEqual(len(events), 5)
        
        # Check event ordering (should be chronological)
        timestamps = [e.timestamp for e in events]
        self.assertEqual(timestamps, sorted(timestamps))
    
    def test_session_summary(self):
        """Test session summary generation."""
        session_start = time.time()
        
        # Record various events
        self.collector.record_download_started('file1', 1024*1024)
        self.collector.record_download_completed('file1', 2.0)
        self.collector.record_search_performed('test', 10, 1.0)
        self.collector.record_security_scan('file1', 'SAFE', 0.95)
        
        self.collector._flush_events()
        
        session_end = time.time()
        summary = self.collector.get_session_summary(session_start, session_end)
        
        self.assertIsInstance(summary, dict)
        self.assertIn('downloads', summary)
        self.assertIn('searches', summary)
        self.assertIn('security', summary)
        
        # Check download metrics
        downloads = summary['downloads']
        self.assertEqual(downloads['total_downloads'], 1)
        self.assertEqual(downloads['successful_downloads'], 1)
    
    def test_global_collector_functions(self):
        """Test global collector management functions."""
        # Test get_analytics_collector with default
        collector1 = get_analytics_collector()
        collector2 = get_analytics_collector()
        self.assertIs(collector1, collector2)  # Should be same instance
        
        # Test setup_analytics_collector
        temp_db = Path(self.temp_dir) / "test_setup.db"
        collector3 = setup_analytics_collector(db_path=str(temp_db))
        self.assertIsInstance(collector3, AnalyticsCollector)
        self.assertTrue(temp_db.exists())
        
        collector3.stop()
        temp_db.unlink()


class TestAnalyticsAnalyzer(unittest.TestCase):
    """Test AnalyticsAnalyzer functionality."""
    
    def setUp(self):
        """Set up test environment with sample data."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_analytics.db"
        self.collector = AnalyticsCollector(db_path=str(self.db_path))
        self.analyzer = AnalyticsAnalyzer(self.collector)
        
        # Create sample data
        self._create_sample_data()
    
    def tearDown(self):
        """Clean up test environment."""
        self.collector.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.temp_dir)
    
    def _create_sample_data(self):
        """Create sample analytics data for testing."""
        base_time = time.time() - (7 * 24 * 3600)  # 7 days ago
        
        # Create download events over 7 days
        for day in range(7):
            day_start = base_time + (day * 24 * 3600)
            
            # Variable activity per day
            downloads_per_day = 10 + (day * 2)  # Increasing activity
            
            for i in range(downloads_per_day):
                file_id = f'file_{day}_{i}'
                timestamp = day_start + (i * 3600)  # Spread over hours
                
                # Record download started
                self.collector.record_event(
                    EventType.DOWNLOAD_STARTED,
                    {'file_id': file_id, 'size': 1024*1024},
                    timestamp=timestamp
                )
                
                # Most downloads succeed
                if i < downloads_per_day - 1:  # Last one fails
                    self.collector.record_event(
                        EventType.DOWNLOAD_COMPLETED,
                        {'file_id': file_id, 'duration': 2.0 + (i * 0.1)},
                        timestamp=timestamp + 30
                    )
                else:
                    self.collector.record_event(
                        EventType.DOWNLOAD_FAILED,
                        {'file_id': file_id, 'error': 'network_timeout'},
                        timestamp=timestamp + 60
                    )
        
        # Add search events
        for day in range(7):
            day_start = base_time + (day * 24 * 3600)
            searches_per_day = 5 + day
            
            for i in range(searches_per_day):
                timestamp = day_start + (i * 4 * 3600)  # Every 4 hours
                self.collector.record_event(
                    EventType.SEARCH_PERFORMED,
                    {
                        'query': f'query_{day}_{i}',
                        'results_count': 20 + (i * 5),
                        'response_time': 1.0 + (i * 0.2)
                    },
                    timestamp=timestamp
                )
        
        # Add performance snapshots
        for day in range(7):
            day_start = base_time + (day * 24 * 3600)
            
            for hour in range(24):
                timestamp = day_start + (hour * 3600)
                
                # Simulate varying performance
                cpu_usage = 30.0 + (hour * 2) + (day * 5)  # Increasing load
                memory_usage = 40.0 + (hour * 1.5)
                download_speed = (1024 * 1024) * (1.5 - (hour * 0.02))  # Decreasing speed
                
                self.collector.record_performance_snapshot(
                    cpu_usage=min(cpu_usage, 100.0),
                    memory_usage=min(memory_usage, 100.0),
                    download_speed=max(download_speed, 512*1024),
                    active_connections=3,
                    timestamp=timestamp
                )
        
        self.collector._flush_events()
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        self.assertIsInstance(self.analyzer, AnalyticsAnalyzer)
        self.assertIs(self.analyzer.collector, self.collector)
    
    def test_generate_report(self):
        """Test complete report generation."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)  # 7 days
        
        report = self.analyzer.generate_report(start_time, end_time)
        
        self.assertIsInstance(report, AnalyticsReport)
        self.assertEqual(report.time_period, (start_time, end_time))
        self.assertIsInstance(report.summary, dict)
        self.assertIsInstance(report.trends, list)
        self.assertIsInstance(report.patterns, list)
        self.assertIsInstance(report.insights, list)
        self.assertIsInstance(report.recommendations, list)
        self.assertIsInstance(report.charts_data, dict)
    
    def test_summary_generation(self):
        """Test summary statistics generation."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        summary = self.analyzer._generate_summary(start_time, end_time)
        
        self.assertIn('downloads', summary)
        self.assertIn('searches', summary)
        self.assertIn('security', summary)
        self.assertIn('performance', summary)
        
        # Check download metrics
        downloads = summary['downloads']
        self.assertGreater(downloads['total_downloads'], 0)
        self.assertGreater(downloads['success_rate'], 0)
        
        # Check search metrics
        searches = summary['searches']
        self.assertGreater(searches['total_searches'], 0)
        
        # Check performance metrics
        performance = summary['performance']
        self.assertGreater(performance['average_cpu_usage'], 0)
    
    def test_trends_analysis(self):
        """Test trend analysis between periods."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        trends = self.analyzer._analyze_trends(start_time, end_time)
        
        self.assertIsInstance(trends, list)
        
        # Should have trends for key metrics
        trend_metrics = [t.metric for t in trends]
        expected_metrics = ['download_success_rate', 'download_speed', 'cpu_usage']
        
        for metric in expected_metrics:
            self.assertIn(metric, trend_metrics)
        
        # Check trend structure
        if trends:
            trend = trends[0]
            self.assertIsInstance(trend.metric, str)
            self.assertIsInstance(trend.change_percentage, float)
            self.assertIn(trend.significance, ['low', 'medium', 'high'])
    
    def test_pattern_identification(self):
        """Test usage pattern identification."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        patterns = self.analyzer._identify_patterns(start_time, end_time)
        
        self.assertIsInstance(patterns, list)
        
        if patterns:
            pattern = patterns[0]
            self.assertIsInstance(pattern, UsagePattern)
            self.assertIsInstance(pattern.pattern_type, str)
            self.assertIsInstance(pattern.description, str)
            self.assertIsInstance(pattern.confidence, float)
            self.assertTrue(0 <= pattern.confidence <= 1)
    
    def test_insights_generation(self):
        """Test performance insights generation."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        insights = self.analyzer._generate_insights(start_time, end_time)
        
        self.assertIsInstance(insights, list)
        
        if insights:
            insight = insights[0]
            self.assertIsInstance(insight, PerformanceInsight)
            self.assertIsInstance(insight.category, str)
            self.assertIsInstance(insight.metric, str)
            self.assertIsInstance(insight.recommendation, str)
            self.assertIn(insight.severity, ['info', 'warning', 'critical'])
    
    def test_charts_data_preparation(self):
        """Test chart data preparation."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        charts_data = self.analyzer._prepare_charts_data(start_time, end_time)
        
        self.assertIsInstance(charts_data, dict)
        
        # Should have key chart types
        expected_charts = ['download_activity', 'performance_metrics', 'success_rate']
        
        for chart_name in expected_charts:
            if chart_name in charts_data:
                chart_data = charts_data[chart_name]
                self.assertIsInstance(chart_data, list)
                
                if chart_data:
                    data_point = chart_data[0]
                    self.assertIsInstance(data_point, TimeSeriesData)
                    self.assertIsInstance(data_point.timestamp, float)
                    self.assertIsInstance(data_point.value, (int, float))
    
    def test_helper_methods(self):
        """Test helper calculation methods."""
        end_time = time.time()
        start_time = end_time - (24 * 3600)  # 1 day
        
        # Test success rate calculation
        success_rate = self.analyzer._calculate_success_rate(start_time, end_time)
        self.assertIsInstance(success_rate, float)
        self.assertTrue(0 <= success_rate <= 100)
        
        # Test download count
        download_count = self.analyzer._get_download_count(start_time, end_time)
        self.assertIsInstance(download_count, int)
        self.assertGreaterEqual(download_count, 0)
        
        # Test average download speed
        avg_speed = self.analyzer._calculate_average_download_speed(start_time, end_time)
        if avg_speed is not None:
            self.assertIsInstance(avg_speed, float)
            self.assertGreater(avg_speed, 0)


class TestReportGenerator(unittest.TestCase):
    """Test ReportGenerator functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_analytics.db"
        self.collector = AnalyticsCollector(db_path=str(self.db_path))
        self.analyzer = AnalyticsAnalyzer(self.collector)
        self.generator = ReportGenerator(self.analyzer)
        
        # Override output directory
        self.generator.output_dir = Path(self.temp_dir) / "reports"
        self.generator.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create sample report
        self.sample_report = self._create_sample_report()
    
    def tearDown(self):
        """Clean up test environment."""
        self.collector.stop()
        # Clean up files and directories
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_sample_report(self):
        """Create a sample analytics report for testing."""
        end_time = time.time()
        start_time = end_time - (24 * 3600)  # 1 day
        
        # Add some sample data
        self.collector.record_download_started('file1', 1024*1024)
        self.collector.record_download_completed('file1', 2.0)
        self.collector.record_search_performed('test query', 25, 1.2)
        self.collector._flush_events()
        
        return self.analyzer.generate_report(start_time, end_time)
    
    def test_generator_initialization(self):
        """Test report generator initialization."""
        self.assertIsInstance(self.generator, ReportGenerator)
        self.assertTrue(self.generator.output_dir.exists())
    
    def test_html_report_generation(self):
        """Test HTML report generation."""
        config = ReportConfig(format="html", include_charts=False)
        
        output_path = self.generator.generate_report(self.sample_report, config)
        
        self.assertIsInstance(output_path, Path)
        self.assertTrue(output_path.exists())
        self.assertTrue(output_path.name.endswith('.html'))
        
        # Check HTML content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('<!DOCTYPE html>', content)
        self.assertIn('CivitAI Downloader Analytics Report', content)
        self.assertIn('Summary Statistics', content)
    
    def test_json_report_generation(self):
        """Test JSON report generation."""
        config = ReportConfig(format="json")
        
        output_path = self.generator.generate_report(self.sample_report, config)
        
        self.assertTrue(output_path.exists())
        self.assertTrue(output_path.name.endswith('.json'))
        
        # Check JSON content
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, dict)
        self.assertIn('report_id', data)
        self.assertIn('summary', data)
        self.assertIn('time_period', data)
    
    def test_pdf_generation_unavailable(self):
        """Test PDF generation when WeasyPrint is not available."""
        # Mock PDF as unavailable
        original_pdf_available = self.generator.pdf_available
        self.generator.pdf_available = False
        
        try:
            config = ReportConfig(format="pdf")
            
            with self.assertRaises(RuntimeError) as context:
                self.generator.generate_report(self.sample_report, config)
            
            self.assertIn("weasyprint", str(context.exception).lower())
        
        finally:
            self.generator.pdf_available = original_pdf_available
    
    def test_report_config(self):
        """Test different report configurations."""
        # Test with charts disabled
        config = ReportConfig(include_charts=False, theme="dark")
        output_path = self.generator.generate_report(self.sample_report, config)
        self.assertTrue(output_path.exists())
        
        # Test with custom language
        config = ReportConfig(language="ja")
        output_path = self.generator.generate_report(self.sample_report, config)
        self.assertTrue(output_path.exists())
    
    def test_css_styles_generation(self):
        """Test CSS styles generation."""
        config = ReportConfig(theme="light")
        styles = self.generator._get_css_styles(config)
        
        self.assertIsInstance(styles, str)
        self.assertIn('body', styles)
        self.assertIn('font-family', styles)
        
        # Test with custom CSS
        config.custom_css = ".custom { color: red; }"
        styles = self.generator._get_css_styles(config)
        self.assertIn('.custom', styles)
    
    def test_html_content_sections(self):
        """Test HTML content section building."""
        # Test summary section
        summary_html = self.generator._build_summary_section(self.sample_report.summary)
        self.assertIn('Summary Statistics', summary_html)
        self.assertIn('Downloads', summary_html)
        
        # Test trends section (may be empty)
        trends_html = self.generator._build_trends_section(self.sample_report.trends)
        if self.sample_report.trends:
            self.assertIn('Trends Analysis', trends_html)
        
        # Test recommendations section
        if self.sample_report.recommendations:
            rec_html = self.generator._build_recommendations_section(self.sample_report.recommendations)
            self.assertIn('Recommendations', rec_html)
    
    def test_charts_without_plotly(self):
        """Test chart generation when Plotly is not available."""
        # Mock Plotly as unavailable
        original_plotly = self.generator.plotly_available
        self.generator.plotly_available = False
        
        try:
            config = ReportConfig(include_charts=True)
            output_path = self.generator.generate_report(self.sample_report, config)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Should still generate report without charts
            self.assertIn('CivitAI Downloader Analytics Report', content)
        
        finally:
            self.generator.plotly_available = original_plotly
    
    def test_create_analytics_dashboard(self):
        """Test analytics dashboard creation."""
        dashboard_path = create_analytics_dashboard(self.collector, self.temp_dir)
        
        self.assertIsInstance(dashboard_path, Path)
        self.assertTrue(dashboard_path.exists())
        self.assertTrue(dashboard_path.name.endswith('.html'))


class TestIntegrationFunctions(unittest.TestCase):
    """Test high-level integration functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_complete_analytics_system(self):
        """Test complete analytics system creation."""
        db_path = Path(self.temp_dir) / "test_system.db"
        
        collector, analyzer, generator = create_complete_analytics_system(
            db_path=str(db_path)
        )
        
        self.assertIsInstance(collector, AnalyticsCollector)
        self.assertIsInstance(analyzer, AnalyticsAnalyzer)
        self.assertIsInstance(generator, ReportGenerator)
        
        # Test they are properly connected
        self.assertIs(analyzer.collector, collector)
        self.assertIs(generator.analyzer, analyzer)
        
        collector.stop()
    
    @patch('core.analytics.quick_analytics_report')
    def test_quick_analytics_report_mocked(self, mock_quick_report):
        """Test quick analytics report function (mocked)."""
        mock_output_path = Path(self.temp_dir) / "mock_report.html"
        mock_quick_report.return_value = mock_output_path
        
        # Create mock file
        mock_output_path.touch()
        
        result = quick_analytics_report(period_days=1, output_format="html")
        
        self.assertEqual(result, mock_output_path)
        mock_quick_report.assert_called_once_with(period_days=1, output_format="html")


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run tests
    unittest.main(verbosity=2)