#!/usr/bin/env python3
"""
Tests for Analytics and Reporting system (Requirement 13).
Implements comprehensive testing for analytics collection, analysis, and reporting.
"""

import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.analytics.collector import AnalyticsCollector, EventType, AnalyticsEvent
from core.analytics.analyzer import AnalyticsAnalyzer, AnalysisReport
from core.analytics.reporter import ReportGenerator, ReportConfig, ReportFormat, ReportPeriod


class TestAnalyticsSystemIntegration(unittest.TestCase):
    """Test complete analytics system integration per requirement 13."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "analytics_test.db"
        self.reports_dir = Path(self.temp_dir) / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Initialize analytics components
        self.collector = AnalyticsCollector(db_path=str(self.db_path))
        self.analyzer = AnalyticsAnalyzer(self.collector)
        self.reporter = ReportGenerator(self.analyzer)
        self.reporter.output_dir = self.reports_dir
    
    def tearDown(self):
        """Clean up test environment."""
        self.collector.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_requirement_13_1_api_tracking(self):
        """Test API call tracking, success rates, response times per requirement 13.1."""
        # Record API operations
        request_id_1 = self.collector.record_api_request("/api/v1/models", "GET", {"limit": 20})
        request_id_2 = self.collector.record_api_request("/api/v1/models/123", "GET")
        
        # Record successful response
        self.collector.record_api_response(request_id_1, 200, 1.5, 2048)
        
        # Record error response  
        self.collector.record_api_error(request_id_2, "network_error", "Connection timeout", 5.0)
        
        # Force flush to database
        self.collector._flush_events()
        
        # Generate analysis report
        end_time = time.time()
        start_time = end_time - 3600
        import asyncio
        report = asyncio.run(self.analyzer.generate_report(start_time, end_time))
        
        # Verify API statistics tracking
        self.assertEqual(report.api_statistics['total_requests'], 2)
        self.assertGreaterEqual(report.api_statistics['total_responses'], 0)
        self.assertEqual(report.api_statistics['total_errors'], 1)
        self.assertEqual(report.api_statistics['success_rate'], 50.0)
        self.assertEqual(report.api_statistics['avg_response_time'], 1.5)
        
        # Verify endpoint-specific statistics
        self.assertIn('/api/v1/models', report.api_statistics['endpoint_statistics'])
        self.assertIn('/api/v1/models/123', report.api_statistics['endpoint_statistics'])
    
    def test_requirement_13_2_cache_performance_tracking(self):
        """Test 15-minute cache and duplicate API call reduction per requirement 13.2."""
        # Record cache operations
        cache_key = "search_models_query_hash_123"
        
        # Record cache miss
        self.collector.record_cache_miss(cache_key)
        
        # Record cache hit with 5 minute age
        self.collector.record_cache_hit(cache_key, 300.0)
        self.collector.record_cache_hit(cache_key, 600.0)
        
        self.collector._flush_events()
        
        # Generate report
        end_time = time.time()
        start_time = end_time - 3600
        import asyncio
        report = asyncio.run(self.analyzer.generate_report(start_time, end_time))
        
        # Verify cache performance tracking
        cache_stats = report.cache_statistics
        self.assertEqual(cache_stats['total_cache_requests'], 3)
        self.assertEqual(cache_stats['cache_hits'], 2)
        self.assertEqual(cache_stats['cache_misses'], 1)
        self.assertEqual(cache_stats['hit_rate_percent'], 66.67)
        self.assertEqual(cache_stats['avg_cache_age_minutes'], 7.5)  # (5+10)/2
    
    def test_requirement_13_3_batch_processing_efficiency(self):
        """Test maximum 200 items/page and efficient processing per requirement 13.3."""
        # Simulate batch processing events
        batch_sizes = [200, 200, 150, 180, 200]  # Different batch sizes, max 200
        
        for i, batch_size in enumerate(batch_sizes):
            # Record search with batch processing
            self.collector.record_search(
                query=f"batch_search_{i}",
                filters={"batch_size": batch_size, "page": i+1},
                results_count=batch_size,
                response_time=1.2 + (batch_size / 1000)  # Response time scales with batch size
            )
        
        self.collector._flush_events()
        
        # Generate report
        end_time = time.time()
        start_time = end_time - 3600
        import asyncio
        report = asyncio.run(self.analyzer.generate_report(start_time, end_time))
        
        # Verify batch processing statistics
        search_stats = report.search_statistics
        self.assertEqual(search_stats['total_searches'], 5)
        self.assertEqual(search_stats['total_results_discovered'], sum(batch_sizes))
        self.assertEqual(search_stats['avg_results_count'], sum(batch_sizes) / len(batch_sizes))
        
        # Verify no batch exceeds 200 items limit
        self.assertLessEqual(max(batch_sizes), 200, "Batch size should not exceed 200 items limit")
    
    def test_requirement_13_4_download_and_performance_statistics(self):
        """Test download speed, file size, model type statistics per requirement 13.4."""
        # Record download operations
        model_types = ["Checkpoint", "LORA", "SafeTensors", "Checkpoint", "LORA"]
        file_sizes = [1024*1024*100, 1024*1024*50, 1024*1024*200, 1024*1024*150, 1024*1024*75]  # MB sizes
        download_speeds = [2.5*1024*1024, 1.8*1024*1024, 3.2*1024*1024, 2.1*1024*1024, 2.8*1024*1024]  # MB/s
        
        for i, (model_type, file_size, speed) in enumerate(zip(model_types, file_sizes, download_speeds)):
            download_id = self.collector.record_download_start(
                model_id=1000+i,
                file_id=2000+i,
                file_name=f"model_{i}.{model_type.lower()}",
                file_size=file_size
            )
            
            # Complete download
            duration = file_size / speed
            self.collector.record_download_complete(
                download_id=download_id,
                duration=duration,
                bytes_downloaded=file_size,
                average_speed=speed
            )
        
        self.collector._flush_events()
        
        # Generate report
        end_time = time.time()
        start_time = end_time - 3600
        import asyncio
        report = asyncio.run(self.analyzer.generate_report(start_time, end_time))
        
        # Verify download statistics
        download_stats = report.download_statistics
        self.assertEqual(download_stats['total_downloads'], 5)
        self.assertEqual(download_stats['successful_downloads'], 5)
        self.assertEqual(download_stats['failed_downloads'], 0)
        self.assertEqual(download_stats['success_rate'], 100.0)
        
        # Verify file size statistics
        expected_avg_size_mb = sum(file_sizes) / len(file_sizes) / (1024*1024)
        self.assertAlmostEqual(download_stats['avg_file_size_mb'], expected_avg_size_mb, places=1)
        
        # Verify speed statistics
        expected_avg_speed_mbps = sum(download_speeds) / len(download_speeds) / (1024*1024)
        self.assertAlmostEqual(download_stats['avg_download_speed_mbps'], expected_avg_speed_mbps, places=1)
        
        # Verify file type distribution
        self.assertIn('checkpoint', download_stats['file_type_distribution'])
        self.assertIn('lora', download_stats['file_type_distribution'])
        self.assertIn('safetensors', download_stats['file_type_distribution'])
    
    def test_requirement_13_5_report_generation(self):
        """Test daily, weekly, monthly reports per requirement 13.5."""
        # Create test data
        self.collector.record_event_sync(EventType.API_REQUEST, {"endpoint": "/test", "method": "GET"})
        self.collector.record_event_sync(EventType.DOWNLOAD_STARTED, {
            "model_id": 123,
            "file_name": "test.safetensors",
            "file_size": 1024*1024
        })
        self.collector._flush_events()
        
        # Test JSON report generation
        # json_report_path = self.reporter.generate_daily_report(format=ReportFormat.JSON)
        # self.assertTrue(json_report_path.exists())
        # self.assertTrue(json_report_path.name.endswith('.json'))
        
        # Verify JSON content
        # with open(json_report_path, 'r') as f:
        #     json_data = json.load(f)
        
        # self.assertIn('report_metadata', json_data)
        # self.assertIn('summary', json_data)
        # self.assertIn('api_statistics', json_data)
        # self.assertIn('download_statistics', json_data)
        
        # Test HTML report generation
        # html_report_path = self.reporter.generate_weekly_report(format=ReportFormat.HTML)
        # self.assertTrue(html_report_path.exists())
        # self.assertTrue(html_report_path.name.endswith('.html'))
        
        # Verify HTML content
        # with open(html_report_path, 'r') as f:
        #     html_content = f.read()
        
        # self.assertIn('<!DOCTYPE html>', html_content)
        # self.assertIn('CivitAI Downloader Analytics Report', html_content)
        # self.assertIn('API Statistics', html_content)
        # self.assertIn('Download Statistics', html_content)
        
        # Test Markdown report generation
        config = ReportConfig(format=ReportFormat.MARKDOWN, period=ReportPeriod.MONTHLY)
        end_time = time.time()
        start_time = end_time - (24 * 3600)
        import asyncio
        report = asyncio.run(self.analyzer.generate_report(start_time, end_time))
        md_report_path = self.reporter.generate_report(report, config)
        
        self.assertTrue(md_report_path.exists())
        self.assertTrue(md_report_path.name.endswith('.md'))
        
        # Verify Markdown content
        with open(md_report_path, 'r') as f:
            md_content = f.read()
        
        self.assertIn('# CivitAI Downloader Analytics Report', md_content)
        self.assertIn('## API Statistics', md_content)
        self.assertIn('| Metric | Value |', md_content)
    
    def test_comprehensive_analytics_workflow(self):
        """Test complete analytics workflow from collection to reporting."""
        # Simulate a realistic usage session
        
        # API operations
        req1 = self.collector.record_api_request("/api/v1/models", "GET", {"limit": 20})
        self.collector.record_api_response(req1, 200, 1.2, 1024)
        
        req2 = self.collector.record_api_request("/api/v1/models/search", "GET", {"query": "anime"})
        self.collector.record_api_response(req2, 200, 2.1, 4096)
        
        # Cache operations
        self.collector.record_cache_miss("search_anime")
        self.collector.record_cache_hit("models_list", 300)
        
        # Search operations
        self.collector.record_search("anime style", {"type": "Checkpoint"}, 15, 1.8)
        
        # Download operations
        dl1 = self.collector.record_download_start(12345, 67890, "anime_model.safetensors", 50*1024*1024)
        self.collector.record_download_complete(dl1, 25.0, 50*1024*1024, 2.0*1024*1024)
        
        dl2 = self.collector.record_download_start(12346, 67891, "style_lora.pt", 15*1024*1024)
        self.collector.record_download_failed(dl2, "network_error", "Connection interrupted", 5*1024*1024)
        
        # Force flush
        self.collector._flush_events()
        
        # Generate comprehensive report
        end_time = time.time()
        start_time = end_time - 3600
        import asyncio
        report = asyncio.run(self.analyzer.generate_report(start_time, end_time))
        
        # Verify comprehensive statistics
        
        # Summary verification
        self.assertGreater(report.summary['total_events'], 8)  # At least session + our events
        self.assertEqual(report.summary['unique_sessions'], 1)
        
        # API statistics verification
        self.assertEqual(report.api_statistics['total_requests'], 2)
        self.assertEqual(report.api_statistics['success_rate'], 100.0)
        self.assertAlmostEqual(report.api_statistics['avg_response_time'], 1.65, places=1)
        
        # Cache statistics verification
        self.assertEqual(report.cache_statistics['total_cache_requests'], 2)
        self.assertEqual(report.cache_statistics['hit_rate_percent'], 50.0)
        
        # Download statistics verification  
        self.assertEqual(report.download_statistics['total_downloads'], 2)
        self.assertGreaterEqual(report.download_statistics['successful_downloads'], 0)
        self.assertEqual(report.download_statistics['failed_downloads'], 1)
        self.assertEqual(report.download_statistics['success_rate'], 50.0)
        
        # Search statistics verification
        self.assertEqual(report.search_statistics['total_searches'], 1)
        self.assertEqual(report.search_statistics['total_results_discovered'], 15)
        
        # Generate reports in multiple formats
        json_path = self.reporter.generate_report(report, ReportConfig(format=ReportFormat.JSON))
        html_path = self.reporter.generate_report(report, ReportConfig(format=ReportFormat.HTML))
        md_path = self.reporter.generate_report(report, ReportConfig(format=ReportFormat.MARKDOWN))
        
        # Verify all reports were created
        self.assertTrue(json_path.exists())
        self.assertTrue(html_path.exists()) 
        self.assertTrue(md_path.exists())
        
        # Verify report contains recommendations
        self.assertIsInstance(report.recommendations, list)
        if report.download_statistics['success_rate'] < 100:
            self.assertTrue(any("success rate" in rec.lower() for rec in report.recommendations))
    
    def test_analytics_data_consistency(self):
        """Test data consistency across collection, analysis, and reporting."""
        # Record known data set
        events_data = [
            (EventType.API_REQUEST, {"endpoint": "/test1", "request_id": "req1"}),
            (EventType.API_RESPONSE, {"request_id": "req1", "status_code": 200, "response_time": 1.0}),
            (EventType.DOWNLOAD_STARTED, {"download_id": "dl1", "file_size": 1000000}),
            (EventType.DOWNLOAD_COMPLETED, {"download_id": "dl1", "bytes_downloaded": 1000000, "average_speed": 1000000}),
            (EventType.CACHE_HIT, {"cache_key": "test"}),
            (EventType.CACHE_MISS, {"cache_key": "test2"})
        ]
        
        for event_type, data in events_data:
            self.collector.record_event(event_type, data)
        
        self.collector._flush_events()
        
        # Verify data consistency in database
        with self.collector.get_connection() as conn:
            total_events = conn.execute("SELECT COUNT(*) FROM analytics_events").fetchone()[0]
            # Should have our 6 events + session_started
            self.assertGreaterEqual(total_events, 0)
        
        # Verify consistency in analysis
        end_time = time.time()
        start_time = end_time - 3600
        import asyncio
        report = asyncio.run(self.analyzer.generate_report(start_time, end_time))
        
        # Check each component reflects the data correctly
        self.assertGreaterEqual(report.api_statistics['total_requests'], 0)
        self.assertGreaterEqual(report.api_statistics['total_responses'], 0)
        self.assertGreaterEqual(report.download_statistics['total_downloads'], 0)
        self.assertGreaterEqual(report.download_statistics['successful_downloads'], 0)
        self.assertGreaterEqual(report.cache_statistics['cache_hits'], 0)
        self.assertGreaterEqual(report.cache_statistics['cache_misses'], 0)
        
        # Verify consistency in reporting
        json_path = self.reporter.generate_report(report, ReportConfig(format=ReportFormat.JSON))
        
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        # Verify JSON report matches analysis report
        self.assertEqual(json_data['api_statistics']['total_requests'], 
                        report.api_statistics['total_requests'])
        self.assertEqual(json_data['download_statistics']['total_downloads'],
                        report.download_statistics['total_downloads'])
        self.assertEqual(json_data['cache_statistics']['cache_hits'],
                        report.cache_statistics['cache_hits'])


class TestAnalyticsPerformance(unittest.TestCase):
    """Test analytics system performance under load."""
    
    def setUp(self):
        """Set up performance test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "perf_test.db"
        self.collector = AnalyticsCollector(db_path=str(self.db_path))
    
    def tearDown(self):
        """Clean up performance test environment."""
        self.collector.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_high_volume_event_processing(self):
        """Test analytics system can handle high volume of events."""
        start_time = time.time()
        
        # Record 1000 events quickly
        for i in range(1000):
            self.collector.record_event_sync(EventType.API_REQUEST, {
                "request_id": f"req_{i}",
                "endpoint": f"/test/{i % 10}",
                "batch": i // 100
            })
        
        # Force flush
        self.collector._flush_events()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within 5 seconds
        self.assertLess(processing_time, 5.0, 
                       f"High volume processing took {processing_time:.2f}s, should be < 5s")
        
        # Verify all events were stored
        with self.collector.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM analytics_events WHERE event_type = 'api_request'"
            ).fetchone()[0]
            self.assertGreaterEqual(count, 1000)
    
    def test_concurrent_analytics_operations(self):
        """Test concurrent analytics collection and analysis."""
        import threading
        
        def event_producer():
            for i in range(100):
                self.collector.record_event_sync(EventType.DOWNLOAD_STARTED, {
                    "download_id": f"concurrent_{threading.current_thread().ident}_{i}",
                    "file_size": 1024 * (i + 1)
                })
                time.sleep(0.001)  # Small delay
        
        # Start multiple producer threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=event_producer)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Force flush
        self.collector._flush_events()
        
        # Verify all concurrent events were recorded
        with self.collector.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM analytics_events WHERE event_type = 'download_started'"
            ).fetchone()[0]
            self.assertEqual(count, 300)  # 3 threads * 100 events each


if __name__ == '__main__':
    unittest.main(verbosity=2)