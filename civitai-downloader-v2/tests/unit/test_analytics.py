#!/usr/bin/env python3
"""
Tests for Analytics System (Phase 4.3).
"""

import pytest
import tempfile
import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

# Import modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.analytics.collector import (
    AnalyticsCollector, EventType, AnalyticsEvent, 
    DownloadMetrics, SearchMetrics, SecurityMetrics,
    get_analytics_collector, setup_analytics_collector
)
from core.analytics.analyzer import (
    AnalyticsAnalyzer, TrendAnalysis, UsagePattern, 
    PerformanceInsight, AnalyticsReport, TimeSeriesData
)
from core.analytics.reporter import ReportGenerator, ReportConfig, create_analytics_dashboard
from core.config.system_config import SystemConfig


class TestAnalyticsCollector:
    """Test analytics data collector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_analytics.db"
        
        # Create collector with test configuration
        self.config = SystemConfig()
        self.collector = AnalyticsCollector(
            config=self.config,
            db_path=self.db_path
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if hasattr(self, 'collector'):
            self.collector.stop()
        
        # Clean up temp files
        if self.db_path.exists():
            self.db_path.unlink()
    
    def test_collector_initialization(self):
        """Test analytics collector initialization."""
        assert self.collector.db_path == self.db_path
        assert self.collector.session_id
        assert self.collector.user_id
        assert self.collector._running
        assert self.db_path.exists()
    
    def test_database_schema(self):
        """Test database schema creation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check events table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
            assert cursor.fetchone() is not None
            
            # Check performance_history table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_history'")
            assert cursor.fetchone() is not None
            
            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_events_timestamp'")
            assert cursor.fetchone() is not None
    
    def test_record_event(self):
        """Test basic event recording."""
        # Record test event
        self.collector.record_event(
            EventType.USER_ACTION,
            {'action': 'test', 'value': 123},
            tags=['test'],
            metadata={'test_meta': 'value'}
        )
        
        # Flush events
        self.collector._flush_events()
        
        # Verify event was stored
        events = self.collector.query_events(EventType.USER_ACTION, limit=1)
        assert len(events) == 1
        
        event = events[0]
        assert event['event_type'] == 'user_action'
        assert event['data']['action'] == 'test'
        assert event['data']['value'] == 123
        assert event['tags'] == ['test']
        assert event['metadata']['test_meta'] == 'value'
    
    def test_download_event_recording(self):
        """Test download event recording."""
        # Mock download task
        mock_task = Mock()
        mock_task.id = "task_123"
        mock_task.file_info = Mock()
        mock_task.file_info.id = "file_456"
        mock_task.file_info.name = "test_model.safetensors"
        mock_task.file_info.size = 1024 * 1024  # 1MB
        mock_task.file_info.metadata = {'model_id': 789}
        mock_task.final_path = Path("/test/path")
        
        # Record download events
        self.collector.record_download_started(mock_task)
        time.sleep(0.1)  # Small delay
        self.collector.record_download_completed(mock_task)
        
        # Flush events
        self.collector._flush_events()
        
        # Verify events
        events = self.collector.query_events(limit=10)
        download_events = [e for e in events if 'download' in e['event_type']]
        assert len(download_events) >= 2
        
        # Check download metrics
        metrics = self.collector.get_download_metrics()
        assert metrics.total_downloads >= 1
        assert metrics.successful_downloads >= 1
    
    def test_search_event_recording(self):
        """Test search event recording."""
        # Mock search results
        mock_results = [Mock(id=i) for i in range(5)]
        
        self.collector.record_search_performed(
            query="test query",
            filters={'tags': ['anime', 'character']},
            results=mock_results,
            response_time=0.5
        )
        
        # Flush events
        self.collector._flush_events()
        
        # Verify search metrics
        metrics = self.collector.get_search_metrics()
        assert metrics.total_searches >= 1
        assert metrics.total_results_returned >= 5
        assert len(metrics.search_response_times) >= 1
    
    def test_security_event_recording(self):
        """Test security scan event recording."""
        # Mock scan report
        mock_report = Mock()
        mock_report.file_path = Path("/test/file.exe")
        mock_report.scan_result = Mock()
        mock_report.scan_result.value = "safe"
        mock_report.file_type = "executable"
        mock_report.file_size = 2048
        mock_report.scan_duration = 1.5
        mock_report.issues = []
        
        self.collector.record_security_scan(mock_report)
        
        # Flush events
        self.collector._flush_events()
        
        # Verify security metrics
        metrics = self.collector.get_security_metrics()
        assert metrics.total_scans >= 1
        assert metrics.safe_files >= 1
    
    def test_bulk_job_recording(self):
        """Test bulk job event recording."""
        # Mock bulk job
        mock_job = Mock()
        mock_job.job_id = "bulk_123"
        mock_job.name = "Test Bulk Job"
        mock_job.total_files = 10
        mock_job.total_size = 1024 * 1024 * 100  # 100MB
        mock_job.search_results = [Mock() for _ in range(3)]
        mock_job.options = {'batch_size': 5}
        mock_job.status = Mock()
        mock_job.status.value = "completed"
        mock_job.downloaded_files = 8
        mock_job.failed_files = 2
        mock_job.skipped_files = 0
        mock_job.downloaded_size = 1024 * 1024 * 80  # 80MB
        mock_job.started_at = time.time() - 300  # 5 minutes ago
        mock_job.completed_at = time.time()
        
        # Record bulk job events
        self.collector.record_bulk_job_created(mock_job)
        self.collector.record_bulk_job_completed(mock_job)
        
        # Flush events
        self.collector._flush_events()
        
        # Verify events recorded
        events = self.collector.query_events(limit=10)
        bulk_events = [e for e in events if 'bulk' in e['event_type']]
        assert len(bulk_events) >= 2
    
    def test_performance_recording(self):
        """Test performance metrics recording."""
        # Mock performance metrics
        mock_metrics = Mock()
        mock_metrics.cpu_usage = 45.5
        mock_metrics.memory_usage = 60.2
        mock_metrics.download_speed = 5 * 1024 * 1024  # 5 MB/s
        mock_metrics.active_connections = 3
        mock_metrics.network_condition = Mock()
        mock_metrics.network_condition.value = "good"
        
        self.collector.record_performance_sample(mock_metrics)
        
        # Verify performance snapshots before flush
        assert len(self.collector.performance_snapshots) >= 1
        
        # Flush events
        self.collector._flush_events()
        
        # After flush, snapshots are cleared, but event should be recorded
        events = self.collector.query_events(EventType.PERFORMANCE_SAMPLE, limit=1)
        assert len(events) >= 1
        
        performance_event = events[0]
        assert performance_event['event_type'] == 'performance_sample'
        assert performance_event['data']['cpu_usage'] == 45.5
    
    def test_event_querying(self):
        """Test event querying functionality."""
        # Record multiple events
        for i in range(5):
            self.collector.record_event(
                EventType.USER_ACTION,
                {'action': f'test_{i}'},
                tags=[f'tag_{i}']
            )
        
        self.collector._flush_events()
        
        # Query all events
        all_events = self.collector.query_events(limit=10)
        assert len(all_events) >= 5
        
        # Query specific event type
        user_events = self.collector.query_events(EventType.USER_ACTION)
        assert len(user_events) >= 5
        
        # Query with time filter
        now = time.time()
        recent_events = self.collector.query_events(
            start_time=now - 3600,  # Last hour
            end_time=now
        )
        assert len(recent_events) >= 5
    
    def test_session_summary(self):
        """Test session summary generation."""
        # Record some events
        self.collector.record_event(EventType.USER_ACTION, {'test': 'data'})
        
        summary = self.collector.get_session_summary()
        
        assert 'session_id' in summary
        assert 'user_id' in summary
        assert 'download_metrics' in summary
        assert 'search_metrics' in summary
        assert 'security_metrics' in summary
        assert 'event_count' in summary
    
    def test_global_collector_functions(self):
        """Test global collector functions."""
        # Test get_analytics_collector
        global_collector = get_analytics_collector()
        assert isinstance(global_collector, AnalyticsCollector)
        
        # Test setup_analytics_collector
        custom_collector = setup_analytics_collector(self.config, self.db_path)
        assert isinstance(custom_collector, AnalyticsCollector)
        
        # Cleanup
        global_collector.stop()
        custom_collector.stop()


class TestAnalyticsAnalyzer:
    """Test analytics analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary database with test data
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_analytics.db"
        
        self.collector = AnalyticsCollector(db_path=self.db_path)
        self.analyzer = AnalyticsAnalyzer(self.collector)
        
        # Populate with test data
        self._populate_test_data()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if hasattr(self, 'collector'):
            self.collector.stop()
        
        if self.db_path.exists():
            self.db_path.unlink()
    
    def _populate_test_data(self):
        """Populate database with test analytics data."""
        base_time = time.time() - (7 * 24 * 3600)  # 7 days ago
        
        # Add download events
        for i in range(20):
            event_time = base_time + (i * 3600)  # Events every hour
            
            # Download started
            self.collector.record_event(
                EventType.DOWNLOAD_STARTED,
                {
                    'task_id': f'task_{i}',
                    'file_id': f'file_{i}',
                    'file_name': f'model_{i}.safetensors',
                    'file_size': 1024 * 1024 * (i + 1),  # Increasing sizes
                    'model_metadata': {'model_id': i}
                },
                tags=['download', 'start']
            )
            
            # Download completed (90% success rate)
            if i < 18:
                self.collector.record_event(
                    EventType.DOWNLOAD_COMPLETED,
                    {
                        'task_id': f'task_{i}',
                        'file_id': f'file_{i}',
                        'file_name': f'model_{i}.safetensors',
                        'file_size': 1024 * 1024 * (i + 1),
                        'duration': 30 + (i * 2),
                        'download_speed': 1024 * 1024 * 2,  # 2 MB/s
                        'model_metadata': {'model_id': i}
                    },
                    tags=['download', 'success']
                )
        
        # Add search events
        for i in range(10):
            event_time = base_time + (i * 3600 * 2)
            self.collector.record_event(
                EventType.SEARCH_PERFORMED,
                {
                    'query': f'query_{i}',
                    'filters': {'tags': ['anime', 'character']},
                    'result_count': 15 + i,
                    'response_time': 0.3 + (i * 0.1)
                },
                tags=['search']
            )
        
        # Add security scan events
        for i in range(15):
            event_time = base_time + (i * 3600 * 1.5)
            self.collector.record_event(
                EventType.SECURITY_SCAN,
                {
                    'file_path': f'/test/file_{i}.exe',
                    'scan_result': 'safe' if i < 13 else 'suspicious',
                    'file_type': 'executable',
                    'file_size': 2048 * (i + 1),
                    'scan_duration': 1.0 + (i * 0.1),
                    'issues_count': 0 if i < 13 else 2,
                    'threat_types': [] if i < 13 else ['malware']
                },
                tags=['security', 'scan']
            )
        
        # Add performance samples
        with sqlite3.connect(self.db_path) as conn:
            for i in range(50):
                timestamp = base_time + (i * 600)  # Every 10 minutes
                conn.execute("""
                    INSERT INTO performance_history 
                    (timestamp, cpu_usage, memory_usage, download_speed, 
                     active_connections, network_condition, optimization_mode, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    30 + (i % 40),  # CPU 30-70%
                    40 + (i % 30),  # Memory 40-70%
                    (1 + (i % 5)) * 1024 * 1024,  # Speed 1-5 MB/s
                    2 + (i % 3),  # Connections 2-4
                    'good',
                    'adaptive',
                    self.collector.session_id
                ))
            conn.commit()
        
        # Flush events
        self.collector._flush_events()
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        assert self.analyzer.collector == self.collector
        assert self.analyzer.db_path == self.db_path
        assert isinstance(self.analyzer.trend_significance_threshold, float)
        assert isinstance(self.analyzer.performance_benchmark, dict)
    
    def test_generate_report(self):
        """Test report generation."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)  # Last 7 days
        
        report = self.analyzer.generate_report(start_time, end_time)
        
        assert isinstance(report, AnalyticsReport)
        assert report.report_id
        assert report.generated_at > 0
        assert report.time_period == (start_time, end_time)
        assert isinstance(report.summary, dict)
        assert isinstance(report.trends, list)
        assert isinstance(report.patterns, list)
        assert isinstance(report.insights, list)
        assert isinstance(report.recommendations, list)
        assert isinstance(report.charts_data, dict)
    
    def test_summary_generation(self):
        """Test summary statistics generation."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        summary = self.analyzer._generate_summary(start_time, end_time)
        
        assert 'period' in summary
        assert 'downloads' in summary
        assert 'searches' in summary
        assert 'security' in summary
        assert 'performance' in summary
        assert 'errors' in summary
        
        # Check downloads summary
        downloads = summary['downloads']
        assert downloads['total_downloads'] > 0
        assert downloads['successful_downloads'] > 0
        assert downloads['success_rate'] > 0
        assert downloads['total_bytes_downloaded'] > 0
    
    def test_trends_analysis(self):
        """Test trends analysis."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        trends = self.analyzer._analyze_trends(start_time, end_time)
        
        assert isinstance(trends, list)
        
        if trends:  # Only test if trends were found
            trend = trends[0]
            assert isinstance(trend, TrendAnalysis)
            assert trend.metric_name
            assert isinstance(trend.current_value, (int, float))
            assert isinstance(trend.previous_value, (int, float))
            assert isinstance(trend.change_percent, (int, float))
            assert trend.trend_direction in ['up', 'down', 'stable']
            assert trend.significance in ['high', 'medium', 'low']
            assert isinstance(trend.is_improving, bool)
    
    def test_pattern_identification(self):
        """Test usage pattern identification."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        patterns = self.analyzer._identify_patterns(start_time, end_time)
        
        assert isinstance(patterns, list)
        
        if patterns:  # Only test if patterns were found
            pattern = patterns[0]
            assert isinstance(pattern, UsagePattern)
            assert pattern.pattern_type
            assert pattern.description
            assert isinstance(pattern.frequency, int)
            assert isinstance(pattern.confidence, float)
            assert isinstance(pattern.recommendations, list)
    
    def test_insights_generation(self):
        """Test performance insights generation."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        insights = self.analyzer._generate_insights(start_time, end_time)
        
        assert isinstance(insights, list)
        
        if insights:  # Only test if insights were found
            insight = insights[0]
            assert isinstance(insight, PerformanceInsight)
            assert insight.category
            assert insight.metric
            assert isinstance(insight.current_value, (int, float))
            assert isinstance(insight.benchmark_value, (int, float))
            assert insight.impact in ['positive', 'negative', 'neutral']
            assert insight.severity in ['critical', 'warning', 'info']
            assert insight.recommendation
    
    def test_charts_data_preparation(self):
        """Test charts data preparation."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        charts_data = self.analyzer._prepare_charts_data(start_time, end_time)
        
        assert isinstance(charts_data, dict)
        
        # Check expected chart types
        expected_charts = ['download_activity', 'performance_metrics', 'success_rate']
        for chart_name in expected_charts:
            if chart_name in charts_data:
                chart_data = charts_data[chart_name]
                assert isinstance(chart_data, list)
                
                if chart_data:  # Only test if data exists
                    point = chart_data[0]
                    assert isinstance(point, TimeSeriesData)
                    assert isinstance(point.timestamp, (int, float))
                    assert isinstance(point.value, (int, float))
    
    def test_helper_methods(self):
        """Test analyzer helper methods."""
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)
        
        # Test success rate calculation
        success_rate = self.analyzer._calculate_success_rate(start_time, end_time)
        if success_rate is not None:
            assert 0 <= success_rate <= 100
        
        # Test download speed calculation
        avg_speed = self.analyzer._calculate_avg_download_speed(start_time, end_time)
        if avg_speed is not None:
            assert avg_speed >= 0
        
        # Test error rate calculation
        error_rate = self.analyzer._calculate_error_rate(start_time, end_time)
        if error_rate is not None:
            assert 0 <= error_rate <= 100
        
        # Test resource usage calculation
        cpu_usage, memory_usage = self.analyzer._calculate_avg_resource_usage(start_time, end_time)
        if cpu_usage is not None:
            assert 0 <= cpu_usage <= 100
        if memory_usage is not None:
            assert 0 <= memory_usage <= 100


class TestReportGenerator:
    """Test analytics report generator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_analytics.db"
        
        self.collector = AnalyticsCollector(db_path=self.db_path)
        self.analyzer = AnalyticsAnalyzer(self.collector)
        self.generator = ReportGenerator(self.analyzer)
        
        # Generate test report
        end_time = time.time()
        start_time = end_time - (24 * 3600)  # Last 24 hours
        self.test_report = self.analyzer.generate_report(start_time, end_time)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if hasattr(self, 'collector'):
            self.collector.stop()
        
        # Clean up temp files
        if self.db_path.exists():
            self.db_path.unlink()
        
        # Clean up generated reports
        for file in Path(self.temp_dir).glob("*.html"):
            file.unlink()
        for file in Path(self.temp_dir).glob("*.json"):
            file.unlink()
    
    def test_generator_initialization(self):
        """Test report generator initialization."""
        assert self.generator.analyzer == self.analyzer
        assert isinstance(self.generator.output_dir, Path)
        assert isinstance(self.generator.chart_colors, dict)
    
    def test_html_report_generation(self):
        """Test HTML report generation."""
        config = ReportConfig(
            include_charts=False,  # Disable charts to avoid dependencies
            format="html",
            theme="light"
        )
        
        output_path = self.generator.generate_report(self.test_report, config)
        
        assert output_path.exists()
        assert output_path.suffix == ".html"
        
        # Read and verify HTML content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '<!DOCTYPE html>' in content
        assert 'CivitAI Downloader Analytics Report' in content
        assert self.test_report.report_id in content
    
    def test_json_report_generation(self):
        """Test JSON report generation."""
        config = ReportConfig(format="json")
        
        output_path = self.generator.generate_report(self.test_report, config)
        
        assert output_path.exists()
        assert output_path.suffix == ".json"
        
        # Read and verify JSON content
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'report_id' in data
        assert 'generated_at' in data
        assert 'time_period' in data
        assert 'summary' in data
        assert 'trends' in data
        assert 'patterns' in data
        assert 'insights' in data
        assert 'recommendations' in data
        assert 'charts_data' in data
        
        assert data['report_id'] == self.test_report.report_id
    
    @patch('core.analytics.reporter.WEASYPRINT_AVAILABLE', False)
    def test_pdf_generation_unavailable(self):
        """Test PDF generation when weasyprint is unavailable."""
        config = ReportConfig(format="pdf")
        
        with pytest.raises(RuntimeError, match="PDF generation requires weasyprint"):
            self.generator.generate_report(self.test_report, config)
    
    def test_report_config(self):
        """Test report configuration options."""
        # Test different configurations
        configs = [
            ReportConfig(format="html", theme="light", language="en"),
            ReportConfig(format="html", theme="dark", language="ja"),
            ReportConfig(format="json", include_charts=False),
        ]
        
        for config in configs:
            output_path = self.generator.generate_report(self.test_report, config)
            assert output_path.exists()
    
    def test_css_styles_generation(self):
        """Test CSS styles generation."""
        config = ReportConfig(
            theme="light",
            custom_css="body { background: red; }"
        )
        
        css = self.generator._get_css_styles(config)
        
        assert isinstance(css, str)
        assert "font-family:" in css
        assert "background: red;" in css
    
    def test_html_content_sections(self):
        """Test HTML content section building."""
        # Test summary section
        summary_html = self.generator._build_summary_section(self.test_report.summary)
        assert isinstance(summary_html, str)
        assert "Summary Statistics" in summary_html
        
        # Test trends section
        if self.test_report.trends:
            trends_html = self.generator._build_trends_section(self.test_report.trends)
            assert isinstance(trends_html, str)
            assert "Trends Analysis" in trends_html
        
        # Test recommendations section
        if self.test_report.recommendations:
            rec_html = self.generator._build_recommendations_section(self.test_report.recommendations)
            assert isinstance(rec_html, str)
            assert "Recommendations" in rec_html
    
    @patch('core.analytics.reporter.PLOTLY_AVAILABLE', False)
    def test_charts_without_plotly(self):
        """Test chart generation when plotly is unavailable."""
        config = ReportConfig(include_charts=True, format="html")
        
        # Should not raise error, just skip charts
        output_path = self.generator.generate_report(self.test_report, config)
        assert output_path.exists()
    
    def test_create_analytics_dashboard(self):
        """Test dashboard creation function."""
        dashboard_path = create_analytics_dashboard(self.collector, Path(self.temp_dir))
        
        assert dashboard_path.exists()
        assert dashboard_path.suffix == ".html"


class TestDataModels:
    """Test analytics data models."""
    
    def test_analytics_event(self):
        """Test AnalyticsEvent data model."""
        event = AnalyticsEvent(
            event_id="test_123",
            event_type=EventType.DOWNLOAD_STARTED,
            timestamp=time.time(),
            user_id="user_456",
            session_id="session_789",
            data={'file_id': 'file_123'},
            tags=['download', 'test'],
            metadata={'test': 'value'}
        )
        
        # Test to_dict method
        event_dict = event.to_dict()
        assert isinstance(event_dict, dict)
        assert event_dict['event_id'] == "test_123"
        assert event_dict['event_type'] == "download_started"
        assert event_dict['user_id'] == "user_456"
        
        # Test JSON serialization
        data_json = json.loads(event_dict['data'])
        assert data_json['file_id'] == 'file_123'
        
        tags_json = json.loads(event_dict['tags'])
        assert tags_json == ['download', 'test']
    
    def test_download_metrics(self):
        """Test DownloadMetrics data model."""
        metrics = DownloadMetrics(
            total_downloads=100,
            successful_downloads=90,
            failed_downloads=10,
            total_bytes_downloaded=1024 * 1024 * 1000,  # 1GB
            total_download_time=3600  # 1 hour
        )
        
        # Test success rate calculation
        assert metrics.success_rate() == 90.0
        
        # Test average file size calculation
        assert metrics.average_file_size() == (1024 * 1024 * 1000) / 90
    
    def test_search_metrics(self):
        """Test SearchMetrics data model."""
        metrics = SearchMetrics(
            total_searches=10,
            search_response_times=[0.1, 0.2, 0.3, 0.4, 0.5]
        )
        
        # Test average response time calculation
        assert metrics.average_response_time() == 0.3
    
    def test_security_metrics(self):
        """Test SecurityMetrics data model."""
        metrics = SecurityMetrics(
            total_scans=100,
            safe_files=90,
            suspicious_files=8,
            malicious_files=2
        )
        
        # Test threat detection rate calculation
        assert metrics.threat_detection_rate() == 10.0
    
    def test_trend_analysis(self):
        """Test TrendAnalysis data model."""
        # Test improving trend
        trend = TrendAnalysis(
            metric_name="success_rate",
            current_value=95.0,
            previous_value=90.0,
            change_percent=5.56,
            trend_direction="up",
            significance="medium"
        )
        
        assert trend.is_improving == True
        
        # Test declining trend for error metric
        error_trend = TrendAnalysis(
            metric_name="error_count",
            current_value=5.0,
            previous_value=10.0,
            change_percent=-50.0,
            trend_direction="down",
            significance="high"
        )
        
        assert error_trend.is_improving == True  # Lower error count is better
    
    def test_time_series_data(self):
        """Test TimeSeriesData data model."""
        ts_data = TimeSeriesData(
            timestamp=time.time(),
            value=123.45,
            label="Test Data"
        )
        
        assert isinstance(ts_data.timestamp, float)
        assert isinstance(ts_data.value, float)
        assert ts_data.label == "Test Data"
    
    def test_report_config(self):
        """Test ReportConfig data model."""
        config = ReportConfig(
            include_charts=True,
            chart_style="modern",
            format="html",
            theme="dark",
            language="ja"
        )
        
        assert config.include_charts == True
        assert config.chart_style == "modern"
        assert config.format == "html"
        assert config.theme == "dark"
        assert config.language == "ja"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])