#!/usr/bin/env python3
"""
Analytics System Demonstration Script.

This script demonstrates the capabilities of the CivitAI Downloader analytics system
including data collection, analysis, and report generation.
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
    EventType, ReportConfig, create_analytics_dashboard
)


def simulate_download_activities(collector):
    """Simulate realistic download activities."""
    print("📊 Simulating download activities...")
    
    # Simulate 50 downloads over the past week
    base_time = time.time() - (7 * 24 * 3600)  # 7 days ago
    
    for i in range(50):
        # Stagger events over time
        event_time = base_time + (i * 3600)  # Every hour
        
        # Create event with specific timestamp
        from core.analytics.collector import AnalyticsEvent
        import uuid
        
        event = AnalyticsEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.DOWNLOAD_STARTED,
            timestamp=event_time,
            user_id=collector.user_id,
            session_id=collector.session_id,
            data={
                'task_id': f'task_{i}',
                'file_id': f'file_{i}',
                'file_name': f'model_{i % 10}.safetensors',
                'file_size': 1024 * 1024 * (10 + (i % 20)),  # 10-30MB files
                'model_metadata': {
                    'model_id': i % 15,
                    'creator': f'artist_{i % 8}',
                    'type': ['checkpoint', 'lora', 'embedding'][i % 3]
                }
            },
            tags=['download', 'simulation']
        )
        
        with collector._lock:
            collector.event_buffer.append(event)
            collector._update_metrics(event)
        
        # 85% success rate
        if i < 42:
            # Simulate successful download
            collector.record_event(
                EventType.DOWNLOAD_COMPLETED,
                {
                    'task_id': f'task_{i}',
                    'file_id': f'file_{i}',
                    'file_name': f'model_{i % 10}.safetensors',
                    'file_size': 1024 * 1024 * (10 + (i % 20)),
                    'duration': 30 + (i % 60),  # 30-90 seconds
                    'download_speed': 1024 * 1024 * (1 + (i % 5)),  # 1-5 MB/s
                    'final_path': f'/downloads/model_{i}.safetensors',
                    'model_metadata': {
                        'model_id': i % 15,
                        'creator': f'artist_{i % 8}',
                        'type': ['checkpoint', 'lora', 'embedding'][i % 3]
                    }
                },
                tags=['download', 'success', 'simulation']
            )
        else:
            # Simulate failed download
            collector.record_event(
                EventType.DOWNLOAD_FAILED,
                {
                    'task_id': f'task_{i}',
                    'file_id': f'file_{i}',
                    'file_name': f'model_{i % 10}.safetensors',
                    'file_size': 1024 * 1024 * (10 + (i % 20)),
                    'duration': 15 + (i % 30),
                    'error': ['network_timeout', 'file_not_found', 'disk_full'][i % 3],
                    'model_metadata': {
                        'model_id': i % 15,
                        'creator': f'artist_{i % 8}',
                        'type': ['checkpoint', 'lora', 'embedding'][i % 3]
                    }
                },
                tags=['download', 'failure', 'simulation']
            )


def simulate_search_activities(collector):
    """Simulate search activities."""
    print("🔍 Simulating search activities...")
    
    base_time = time.time() - (7 * 24 * 3600)
    search_queries = [
        'anime character', 'realistic portrait', 'fantasy art', 'style lora',
        'background model', 'character design', 'digital art', 'concept art'
    ]
    
    for i in range(20):
        event_time = base_time + (i * 4 * 3600)  # Every 4 hours
        query = search_queries[i % len(search_queries)]
        
        # Create mock search results
        from unittest.mock import Mock
        results = []
        for j in range(15 + (i % 10)):  # 15-25 results
            result = Mock()
            result.id = j + i * 100
            result.name = f'Model {j}'
            results.append(result)
        
        collector.record_search_performed(
            query=query,
            filters={
                'tags': ['anime', 'character'] if 'anime' in query else ['realistic', 'art'],
                'type': ['checkpoint', 'lora'][i % 2],
                'sort': 'popularity'
            },
            results=results,
            response_time=0.2 + (i % 10) * 0.1  # 0.2-1.2 seconds
        )


def simulate_security_scans(collector):
    """Simulate security scan activities."""
    print("🔒 Simulating security scans...")
    
    base_time = time.time() - (7 * 24 * 3600)
    
    for i in range(42):  # Scan all successful downloads
        event_time = base_time + (i * 3600) + 1800  # 30 minutes after download
        
        # Mock scan report
        from unittest.mock import Mock
        scan_report = Mock()
        scan_report.file_path = Path(f'/downloads/model_{i}.safetensors')
        scan_report.scan_result = Mock()
        scan_report.scan_result.value = 'safe' if i < 40 else 'suspicious'  # 95% safe
        scan_report.file_type = 'safetensors'
        scan_report.file_size = 1024 * 1024 * (10 + (i % 20))
        scan_report.scan_duration = 0.5 + (i % 5) * 0.1  # 0.5-1.0 seconds
        scan_report.issues = [] if i < 40 else [Mock()]
        
        collector.record_security_scan(scan_report)


def simulate_performance_metrics(collector):
    """Simulate performance metrics."""
    print("⚡ Simulating performance metrics...")
    
    base_time = time.time() - (7 * 24 * 3600)
    
    for i in range(100):  # Performance samples every hour
        event_time = base_time + (i * 1.5 * 3600)  # Every 1.5 hours
        
        # Mock performance metrics
        from unittest.mock import Mock
        metrics = Mock()
        metrics.cpu_usage = 30 + (i % 40) + (i * 0.1)  # Varying CPU usage
        metrics.memory_usage = 40 + (i % 30) + (i * 0.05)  # Varying memory usage
        metrics.download_speed = (2 + (i % 3)) * 1024 * 1024  # 2-5 MB/s
        metrics.active_connections = 2 + (i % 4)  # 2-5 connections
        metrics.network_condition = Mock()
        metrics.network_condition.value = ['excellent', 'good', 'fair'][i % 3]
        
        collector.record_performance_sample(metrics)


def demonstrate_analytics_system():
    """Demonstrate the complete analytics system."""
    print("🚀 CivitAI Downloader Analytics System Demo")
    print("=" * 50)
    
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "demo_analytics.db"
    
    try:
        # Initialize analytics system
        print("📊 Initializing analytics system...")
        collector = AnalyticsCollector(db_path=db_path)
        analyzer = AnalyticsAnalyzer(collector)
        generator = ReportGenerator(analyzer)
        
        # Simulate activities
        simulate_download_activities(collector)
        simulate_search_activities(collector)
        simulate_security_scans(collector)
        simulate_performance_metrics(collector)
        
        # Flush all events to database
        print("💾 Flushing events to database...")
        collector._flush_events()
        
        # Generate analytics report
        print("📈 Generating analytics report...")
        end_time = time.time()
        start_time = end_time - (7 * 24 * 3600)  # Last 7 days
        
        report = analyzer.generate_report(start_time, end_time)
        
        # Display report summary
        print("\n📊 ANALYTICS REPORT SUMMARY")
        print("-" * 30)
        print(f"Report ID: {report.report_id}")
        print(f"Time Period: {report.time_period[0]:.0f} - {report.time_period[1]:.0f}")
        print(f"Generated At: {report.generated_at:.0f}")
        
        # Display key metrics
        downloads = report.summary.get('downloads', {})
        searches = report.summary.get('searches', {})
        security = report.summary.get('security', {})
        
        print(f"\n📥 Downloads:")
        print(f"  Total: {downloads.get('total_downloads', 0)}")
        print(f"  Successful: {downloads.get('successful_downloads', 0)}")
        print(f"  Success Rate: {downloads.get('success_rate', 0):.1f}%")
        print(f"  Total Size: {downloads.get('total_size_gb', 0):.2f} GB")
        
        print(f"\n🔍 Searches:")
        print(f"  Total: {searches.get('total_searches', 0)}")
        print(f"  Avg Results: {searches.get('average_results_per_search', 0):.1f}")
        print(f"  Avg Response Time: {searches.get('average_response_time', 0):.2f}s")
        
        print(f"\n🔒 Security:")
        print(f"  Total Scans: {security.get('total_scans', 0)}")
        print(f"  Safe Files: {security.get('safe_files', 0)}")
        print(f"  Threat Detection Rate: {security.get('threat_detection_rate', 0):.1f}%")
        
        # Display trends
        if report.trends:
            print(f"\n📈 Trends ({len(report.trends)} identified):")
            for trend in report.trends:
                direction = "📈" if trend.trend_direction == "up" else "📉" if trend.trend_direction == "down" else "➡️"
                print(f"  {direction} {trend.metric_name}: {trend.change_percent:+.1f}%")
        
        # Display patterns
        if report.patterns:
            print(f"\n🔍 Usage Patterns ({len(report.patterns)} identified):")
            for pattern in report.patterns:
                print(f"  • {pattern.description}")
        
        # Display insights
        if report.insights:
            print(f"\n💡 Performance Insights ({len(report.insights)} identified):")
            for insight in report.insights:
                severity_icon = "🚨" if insight.severity == "critical" else "⚠️" if insight.severity == "warning" else "ℹ️"
                print(f"  {severity_icon} {insight.category}: {insight.recommendation}")
        
        # Display recommendations
        if report.recommendations:
            print(f"\n🎯 Recommendations ({len(report.recommendations)} total):")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Generate HTML report
        print(f"\n📄 Generating HTML report...")
        config = ReportConfig(
            include_charts=False,  # Disable charts for demo
            format="html",
            theme="light"
        )
        
        html_path = generator.generate_report(report, config)
        print(f"  ✅ HTML report saved to: {html_path}")
        
        # Generate JSON report
        json_config = ReportConfig(format="json")
        json_path = generator.generate_report(report, json_config)
        print(f"  ✅ JSON report saved to: {json_path}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"Database: {db_path}")
        print(f"Reports saved in: {generator.output_dir}")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if 'collector' in locals():
            collector.stop()


if __name__ == "__main__":
    demonstrate_analytics_system()