#!/usr/bin/env python3
"""
Simplified unit tests for Analytics system.
Tests basic functionality without complex dependencies.
"""

import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.analytics.collector import (
    AnalyticsCollector, EventType, get_analytics_collector
)

try:
    from core.analytics.analyzer import AnalyticsAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False


class TestAnalyticsBasic(unittest.TestCase):
    """Test basic analytics functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_analytics.db"
        self.collector = AnalyticsCollector(db_path=str(self.db_path))
    
    def tearDown(self):
        """Clean up test environment."""
        self.collector.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.temp_dir)
    
    def test_collector_initialization(self):
        """Test basic collector initialization."""
        self.assertTrue(self.db_path.exists())
        self.assertIsInstance(self.collector, AnalyticsCollector)
    
    def test_database_creation(self):
        """Test database and table creation."""
        with sqlite3.connect(self.db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [table[0] for table in tables]
            self.assertIn('events', table_names)
    
    def test_basic_event_recording(self):
        """Test basic event recording."""
        # Record an event directly using the lower-level method
        self.collector.record_event(
            EventType.DOWNLOAD_STARTED,
            {'file_id': 'test123', 'size': 1024}
        )
        
        # Force flush
        self.collector._flush_events()
        
        # Verify event was recorded
        with sqlite3.connect(self.db_path) as conn:
            events = conn.execute("SELECT * FROM events").fetchall()
            print(f"Events found: {len(events)}")
            for event in events:
                print(f"Event: {event}")
            self.assertGreaterEqual(len(events), 1)  # Allow for multiple events
    
    def test_global_collector(self):
        """Test global collector functionality."""
        collector1 = get_analytics_collector()
        collector2 = get_analytics_collector()
        self.assertIs(collector1, collector2)
    
    @unittest.skipIf(not ANALYZER_AVAILABLE, "Analyzer not available")
    def test_analyzer_basic(self):
        """Test basic analyzer functionality."""
        # Add some data
        self.collector.record_event(
            EventType.DOWNLOAD_STARTED,
            {'file_id': 'test123', 'size': 1024}
        )
        self.collector.record_event(
            EventType.DOWNLOAD_COMPLETED,
            {'file_id': 'test123', 'duration': 2.5}
        )
        self.collector._flush_events()
        
        # Create analyzer
        analyzer = AnalyticsAnalyzer(self.collector)
        
        # Generate report
        end_time = time.time()
        start_time = end_time - 3600  # 1 hour ago
        
        report = analyzer.generate_report(start_time, end_time)
        
        # Basic assertions
        self.assertIsNotNone(report)
        self.assertIsInstance(report.summary, dict)


if __name__ == '__main__':
    unittest.main(verbosity=2)