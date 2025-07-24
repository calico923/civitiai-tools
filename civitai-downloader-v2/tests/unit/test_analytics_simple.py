#!/usr/bin/env python3
"""
Simplified unit tests for Analytics system.
Tests basic functionality without complex dependencies.
"""

import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from core.analytics.collector import (
    AnalyticsCollector, EventType, get_analytics_collector
)

try:
    from core.analytics.analyzer import AnalyticsAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False


@pytest.fixture(autouse=True)
def reset_global_collector(monkeypatch):
    """Fixture to reset the global collector instance before each test."""
    # Temporarily set the instance to None
    monkeypatch.setattr("core.analytics.collector._global_collector", None)
    yield
    # After the test, ensure it's cleaned up again
    monkeypatch.setattr("core.analytics.collector._global_collector", None)


@pytest.fixture
def collector(tmp_path):
    """Fixture to create a new AnalyticsCollector for each test."""
    db_path = tmp_path / "test_analytics.db"
    collector = AnalyticsCollector(db_path=str(db_path))
    yield collector
    collector.stop()


def test_collector_initialization(collector, tmp_path):
    """Test basic collector initialization."""
    db_path = tmp_path / "test_analytics.db"
    assert db_path.exists()
    assert isinstance(collector, AnalyticsCollector)


def test_database_creation(collector, tmp_path):
    """Test database and table creation."""
    db_path = tmp_path / "test_analytics.db"
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [table[0] for table in tables]
        assert 'analytics_events' in table_names


@pytest.mark.asyncio
async def test_basic_event_recording(collector, tmp_path):
    """Test basic event recording."""
    db_path = tmp_path / "test_analytics.db"
    # Record an event directly using the lower-level method
    await collector.record_event(
        EventType.DOWNLOAD_STARTED,
        {'file_id': 'test123', 'size': 1024}
    )

    # Force flush
    collector._flush_events()

    # Verify event was recorded
    with sqlite3.connect(db_path) as conn:
        # Use the correct table name 'analytics_events'
        events = conn.execute("SELECT * FROM analytics_events").fetchall()
        print(f"Events found: {len(events)}")
        for event in events:
            print(f"Event: {event}")
        assert len(events) >= 1


def test_global_collector(reset_global_collector):
    """Test global collector functionality."""
    # The fixture already resets the instance
    collector1 = get_analytics_collector()
    collector2 = get_analytics_collector()
    assert collector1 is collector2
    # Clean up the global instance's resources if it was created
    if collector1:
        collector1.stop()


@pytest.mark.skipif(not ANALYZER_AVAILABLE, reason="Analyzer not available")
@pytest.mark.asyncio
async def test_analyzer_basic(collector):
    """Test basic analyzer functionality."""
    # Add some data
    await collector.record_event(
        EventType.DOWNLOAD_STARTED,
        {'file_id': 'test123', 'size': 1024}
    )
    await collector.record_event(
        EventType.DOWNLOAD_COMPLETED,
        {'file_id': 'test123', 'duration': 2.5}
    )
    collector._flush_events()

    # Create analyzer
    analyzer = AnalyticsAnalyzer(collector)

    # Generate report
    end_time = time.time()
    start_time = end_time - 3600  # 1 hour ago

    report = await analyzer.generate_report(start_time, end_time)

    # Basic assertions
    assert report is not None
    assert isinstance(report.summary, dict)


if __name__ == '__main__':
    # This part is for standalone execution, not used by pytest
    pytest.main([__file__])