#!/usr/bin/env python3
"""
Comprehensive unit tests for Analytics system.
Tests actual implementation behavior and integration scenarios.
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

from core.analytics.collector import AnalyticsCollector, EventType
from core.analytics.analyzer import AnalyticsAnalyzer
from core.analytics.reporter import ReportGenerator, ReportConfig


class TestAnalyticsWorkflows(unittest.TestCase):
    """Test real-world analytics workflows."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "analytics.db"
        self.collector = AnalyticsCollector(db_path=str(self.db_path))
        self.analyzer = AnalyticsAnalyzer(self.collector)
    
    def tearDown(self):
        """Clean up test environment."""
        self.collector.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_download_lifecycle_complete(self):
        """Test complete download lifecycle tracking."""
        # Record download lifecycle
        self.collector.record_event(EventType.DOWNLOAD_STARTED, {
            'file_id': 'model_123',
            'size': 1024*1024*100,  # 100MB
            'file_name': 'test_model.safetensors'
        })
        
        self.collector.record_event(EventType.DOWNLOAD_COMPLETED, {
            'file_id': 'model_123',
            'duration': 45.5,
            'final_size': 1024*1024*100,
            'average_speed': 2.2 * 1024 * 1024  # 2.2 MB/s
        })
        
        self.collector._flush_events()
        
        # Verify events were recorded correctly
        with sqlite3.connect(self.db_path) as conn:
            events = conn.execute(
                "SELECT event_type, data FROM events WHERE event_type IN (?, ?) ORDER BY timestamp",
                ('download_started', 'download_completed')
            ).fetchall()
        
        self.assertEqual(len(events), 2)
        
        # Verify data integrity
        start_data = json.loads(events[0][1])
        complete_data = json.loads(events[1][1])
        
        self.assertEqual(start_data['file_id'], 'model_123')
        self.assertEqual(complete_data['file_id'], 'model_123')
        self.assertEqual(complete_data['duration'], 45.5)
    
    def test_analytics_report_generation_with_data(self):
        """Test report generation with meaningful data."""
        # Create realistic data within the analysis time range
        end_time = time.time()
        start_time = end_time - 3600  # 1 hour ago
        base_time = start_time + 300  # Start 5 minutes into the range
        
        # Multiple download events
        for i in range(10):
            self.collector.record_event(EventType.DOWNLOAD_STARTED, {
                'file_id': f'file_{i}',
                'size': 1024 * 1024 * (i + 1)
            }, timestamp=base_time + (i * 300))  # Every 5 minutes
            
            # Most succeed, some fail
            if i < 8:
                self.collector.record_event(EventType.DOWNLOAD_COMPLETED, {
                    'file_id': f'file_{i}',
                    'duration': 30 + (i * 2)
                }, timestamp=base_time + (i * 300) + 30)
            else:
                self.collector.record_event(EventType.DOWNLOAD_FAILED, {
                    'file_id': f'file_{i}',
                    'error': 'network_timeout'
                }, timestamp=base_time + (i * 300) + 60)
        
        # Add some search events
        for i in range(5):
            self.collector.record_event(EventType.SEARCH_PERFORMED, {
                'query': f'search_{i}',
                'results_count': 20 + i * 5,
                'response_time': 1.0 + (i * 0.2)
            }, timestamp=base_time + (i * 600))
        
        self.collector._flush_events()
        
        # Generate report
        report = self.analyzer.generate_report(start_time, end_time)
        
        # Verify meaningful report content
        self.assertIsNotNone(report)
        self.assertIn('downloads', report.summary)
        self.assertIn('searches', report.summary)
        
        downloads = report.summary['downloads']
        self.assertGreater(downloads['total_downloads'], 0)
        self.assertTrue(0 <= downloads['success_rate'] <= 100)
        
        searches = report.summary['searches']
        self.assertGreater(searches['total_searches'], 0)
    
    def test_error_handling_database_corruption(self):
        """Test behavior with database issues."""
        # Force database corruption
        self.collector.stop()
        
        # Corrupt the database file
        with open(self.db_path, 'wb') as f:
            f.write(b'corrupted data')
        
        # Try to create new collector - should handle gracefully
        try:
            new_collector = AnalyticsCollector(db_path=str(self.db_path))
            # Should recreate database
            self.assertTrue(self.db_path.exists())
            new_collector.stop()
        except Exception as e:
            self.fail(f"Should handle database corruption gracefully: {e}")
    
    def test_performance_large_event_volume(self):
        """Test performance with large number of events."""
        import time
        
        start_time = time.time()
        
        # Record 1000 events
        for i in range(1000):
            self.collector.record_event(EventType.DOWNLOAD_STARTED, {
                'file_id': f'file_{i}',
                'size': 1024 * (i + 1)
            })
        
        self.collector._flush_events()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (5 seconds)
        self.assertLess(duration, 5.0, "Large volume processing took too long")
        
        # Verify all events were recorded
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM events WHERE event_type = 'download_started'").fetchone()[0]
            # Account for session_started event
            self.assertGreaterEqual(count, 1000)
    
    def test_report_generator_formats(self):
        """Test report generation in different formats."""
        # Add some data
        self.collector.record_event(EventType.DOWNLOAD_STARTED, {
            'file_id': 'test',
            'size': 1024
        })
        self.collector._flush_events()
        
        # Generate report
        end_time = time.time()
        start_time = end_time - 3600
        report = self.analyzer.generate_report(start_time, end_time)
        
        generator = ReportGenerator(self.analyzer)
        generator.output_dir = Path(self.temp_dir)
        
        # Test JSON format
        json_config = ReportConfig(format="json")
        json_path = generator.generate_report(report, json_config)
        
        self.assertTrue(json_path.exists())
        self.assertTrue(json_path.name.endswith('.json'))
        
        # Verify JSON content is valid
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, dict)
        self.assertIn('summary', data)
        
        # Test HTML format  
        html_config = ReportConfig(format="html", include_charts=False)
        html_path = generator.generate_report(report, html_config)
        
        self.assertTrue(html_path.exists())
        self.assertTrue(html_path.name.endswith('.html'))
        
        # Verify HTML content
        with open(html_path, 'r') as f:
            content = f.read()
        
        self.assertIn('<!DOCTYPE html>', content)
        self.assertIn('Analytics Report', content)
    
    def test_analytics_data_consistency(self):
        """Test data consistency across collector and analyzer."""
        # Record events with known quantities
        events_data = [
            (EventType.DOWNLOAD_STARTED, {'file_id': 'f1', 'size': 1000}),
            (EventType.DOWNLOAD_COMPLETED, {'file_id': 'f1', 'duration': 10}),
            (EventType.DOWNLOAD_STARTED, {'file_id': 'f2', 'size': 2000}),
            (EventType.DOWNLOAD_FAILED, {'file_id': 'f2', 'error': 'timeout'}),
            (EventType.SEARCH_PERFORMED, {'query': 'test', 'results_count': 25, 'response_time': 1.5})
        ]
        
        for event_type, data in events_data:
            self.collector.record_event(event_type, data)
        
        self.collector._flush_events()
        
        # Generate report and verify data consistency
        end_time = time.time()
        start_time = end_time - 3600
        report = self.analyzer.generate_report(start_time, end_time)
        
        # Check download metrics
        downloads = report.summary['downloads']
        self.assertEqual(downloads['total_downloads'], 2)
        self.assertEqual(downloads['successful_downloads'], 1)
        self.assertEqual(downloads['failed_downloads'], 1)
        self.assertEqual(downloads['success_rate'], 50.0)
        
        # Check search metrics
        searches = report.summary['searches']
        self.assertEqual(searches['total_searches'], 1)
    
    def test_concurrent_access_safety(self):
        """Test thread safety with concurrent access."""
        import threading
        import random
        
        def worker(worker_id, num_events):
            for i in range(num_events):
                self.collector.record_event(EventType.DOWNLOAD_STARTED, {
                    'file_id': f'worker_{worker_id}_file_{i}',
                    'size': random.randint(1000, 10000)
                })
                # Small random delay to simulate real usage
                time.sleep(random.uniform(0.001, 0.005))
        
        # Start multiple worker threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker, args=(worker_id, 20))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        self.collector._flush_events()
        
        # Verify all events were recorded (100 + session events)
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM events WHERE event_type = 'download_started'").fetchone()[0]
            self.assertGreaterEqual(count, 100)


class TestAnalyticsEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "edge_test.db"
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_empty_database_report_generation(self):
        """Test report generation with no data."""
        collector = AnalyticsCollector(db_path=str(self.db_path))
        analyzer = AnalyticsAnalyzer(collector)
        
        try:
            end_time = time.time()
            start_time = end_time - 3600
            report = analyzer.generate_report(start_time, end_time)
            
            # Should not crash, should return empty/zero metrics
            self.assertIsNotNone(report)
            self.assertIsInstance(report.summary, dict)
            
            # Download metrics should exist but be zero
            if 'downloads' in report.summary:
                downloads = report.summary['downloads']
                self.assertEqual(downloads.get('total_downloads', 0), 0)
        
        finally:
            collector.stop()
    
    def test_invalid_event_data_handling(self):
        """Test handling of invalid event data."""
        collector = AnalyticsCollector(db_path=str(self.db_path))
        
        try:
            # Test with invalid JSON data
            collector.record_event(EventType.DOWNLOAD_STARTED, {
                'invalid_data': float('inf')  # Cannot be JSON serialized
            })
            
            # Should not crash - error should be logged and ignored
            collector._flush_events()
            
            # Should still be functional
            collector.record_event(EventType.DOWNLOAD_STARTED, {
                'file_id': 'valid_file',
                'size': 1024
            })
            collector._flush_events()
            
            # Verify valid event was recorded
            with sqlite3.connect(self.db_path) as conn:
                events = conn.execute("SELECT * FROM events WHERE event_type = 'download_started'").fetchall()
                # Should have at least the valid event (plus any session events)
                self.assertGreaterEqual(len(events), 1)
        
        finally:
            collector.stop()


if __name__ == '__main__':
    unittest.main(verbosity=2)