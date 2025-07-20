#!/usr/bin/env python3
"""
Simple Analytics System Demonstration.

This script demonstrates basic analytics functionality with minimal setup.
"""

import time
import tempfile
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.analytics import (
    AnalyticsCollector, AnalyticsAnalyzer, ReportGenerator,
    EventType, ReportConfig
)


def demo_basic_analytics():
    """Demonstrate basic analytics functionality."""
    print("🚀 Simple Analytics Demo")
    print("=" * 30)
    
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "simple_demo.db"
    
    try:
        # Initialize analytics system
        print("📊 Initializing analytics system...")
        collector = AnalyticsCollector(db_path=db_path)
        analyzer = AnalyticsAnalyzer(collector)
        generator = ReportGenerator(analyzer)
        
        # Record some simple events
        print("📝 Recording test events...")
        
        # User action events
        collector.record_event(EventType.USER_ACTION, {
            'action': 'demo_started',
            'version': '1.0.0'
        })
        
        # Simulate some download activity
        for i in range(5):
            collector.record_event(EventType.DOWNLOAD_STARTED, {
                'task_id': f'demo_task_{i}',
                'file_name': f'demo_model_{i}.safetensors',
                'file_size': 1024 * 1024 * (i + 1)  # 1-5 MB
            })
            
            if i < 4:  # 80% success rate
                collector.record_event(EventType.DOWNLOAD_COMPLETED, {
                    'task_id': f'demo_task_{i}',
                    'file_name': f'demo_model_{i}.safetensors',
                    'file_size': 1024 * 1024 * (i + 1),
                    'duration': 10 + i,
                    'download_speed': 1024 * 1024  # 1 MB/s
                })
        
        # Record search activity
        collector.record_event(EventType.SEARCH_PERFORMED, {
            'query': 'demo search',
            'result_count': 10,
            'response_time': 0.5
        })
        
        # Record error
        collector.record_event(EventType.ERROR_OCCURRED, {
            'error_type': 'demo_error',
            'error_message': 'This is a demo error'
        })
        
        # Flush events
        print("💾 Flushing events...")
        collector._flush_events()
        
        # Generate report
        print("📈 Generating analytics report...")
        end_time = time.time()
        start_time = end_time - (24 * 3600)  # Last 24 hours
        
        report = analyzer.generate_report(start_time, end_time)
        
        # Display basic info
        print(f"\n📊 Report Generated:")
        print(f"  Report ID: {report.report_id}")
        print(f"  Events Analyzed: {len(collector.query_events(limit=100))}")
        print(f"  Trends Found: {len(report.trends)}")
        print(f"  Patterns Found: {len(report.patterns)}")
        print(f"  Insights Found: {len(report.insights)}")
        print(f"  Recommendations: {len(report.recommendations)}")
        
        # Generate reports
        print(f"\n📄 Generating report files...")
        
        # HTML report
        html_config = ReportConfig(format="html", include_charts=False)
        html_path = generator.generate_report(report, html_config)
        print(f"  ✅ HTML: {html_path}")
        
        # JSON report
        json_config = ReportConfig(format="json")
        json_path = generator.generate_report(report, json_config)
        print(f"  ✅ JSON: {json_path}")
        
        # Show summary
        if report.summary:
            downloads = report.summary.get('downloads', {})
            if downloads:
                print(f"\n📥 Download Summary:")
                print(f"  Total: {downloads.get('total_downloads', 0)}")
                print(f"  Success Rate: {downloads.get('success_rate', 0):.1f}%")
        
        if report.recommendations:
            print(f"\n🎯 Sample Recommendations:")
            for i, rec in enumerate(report.recommendations[:3], 1):
                print(f"  {i}. {rec}")
        
        print(f"\n✅ Demo completed successfully!")
        print(f"Database: {db_path}")
        print(f"Reports: {generator.output_dir}")
        
        # Show file sizes
        print(f"\nFile sizes:")
        if html_path.exists():
            print(f"  HTML: {html_path.stat().st_size:,} bytes")
        if json_path.exists():
            print(f"  JSON: {json_path.stat().st_size:,} bytes")
        if db_path.exists():
            print(f"  Database: {db_path.stat().st_size:,} bytes")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'collector' in locals():
            collector.stop()


if __name__ == "__main__":
    demo_basic_analytics()