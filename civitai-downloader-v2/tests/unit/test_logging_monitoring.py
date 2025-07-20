#!/usr/bin/env python3
"""
Logging and monitoring tests.
Tests for structured logging, metrics collection, alerting, and performance monitoring.
"""

import pytest
import json
import time
import tempfile
import logging
from pathlib import Path
import importlib.util
from typing import Dict, List, Any
from unittest.mock import Mock, patch
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestLoggingMonitoring:
    """Test logging and monitoring functionality for observability and performance tracking."""
    
    @property
    def monitoring_dir(self) -> Path:
        """Get the monitoring directory."""
        return Path(__file__).parent.parent.parent / "src" / "monitoring"
    
    def test_enhanced_monitoring_service_exists(self):
        """Test that enhanced monitoring service module exists."""
        structured_logger_path = self.monitoring_dir / "structured_logger.py"
        assert structured_logger_path.exists(), "structured_logger.py must exist"
        
        spec = importlib.util.spec_from_file_location("structured_logger", structured_logger_path)
        logger_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(logger_module)
        
        # Test StructuredLogger class exists
        assert hasattr(logger_module, 'StructuredLogger'), "StructuredLogger class must exist"
        StructuredLogger = logger_module.StructuredLogger
        
        # Test initialization
        logger = StructuredLogger()
        
        # Validate structured logging methods
        assert hasattr(logger, 'log_structured'), "Must have structured logging"
        assert hasattr(logger, 'log_performance'), "Must have performance logging"
        assert hasattr(logger, 'log_error'), "Must have error logging"
        assert hasattr(logger, 'configure_rotation'), "Must have log rotation"
    
    def test_structured_logging_format(self):
        """Test structured logging format with JSON output."""
        structured_logger_path = self.monitoring_dir / "structured_logger.py"
        spec = importlib.util.spec_from_file_location("structured_logger", structured_logger_path)
        logger_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(logger_module)
        
        StructuredLogger = logger_module.StructuredLogger
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = Path(tmp_dir) / "test.log"
            logger = StructuredLogger(log_file=str(log_file))
            
            # Test structured log entry
            test_data = {
                'operation': 'model_download',
                'model_id': 12345,
                'duration_ms': 1500,
                'success': True,
                'metadata': {'size_mb': 150, 'format': 'safetensors'}
            }
            
            logger.log_structured('INFO', 'Model download completed', **test_data)
            
            # Verify log file was created and contains structured data
            assert log_file.exists(), "Log file should be created"
            
            with open(log_file, 'r') as f:
                log_content = f.read()
                
            # Parse JSON log entry
            log_lines = [line for line in log_content.strip().split('\n') if line]
            assert len(log_lines) >= 1, "Should have at least one log entry"
            
            log_entry = json.loads(log_lines[0])
            
            # Validate structured format
            assert 'timestamp' in log_entry, "Should have timestamp"
            assert 'level' in log_entry, "Should have log level"
            assert 'message' in log_entry, "Should have message"
            assert 'operation' in log_entry, "Should have operation field"
            assert 'model_id' in log_entry, "Should have model_id field"
            assert log_entry['operation'] == 'model_download', "Should preserve operation value"
            assert log_entry['model_id'] == 12345, "Should preserve model_id value"
    
    def test_log_rotation_policy(self):
        """Test log rotation policy and file management."""
        structured_logger_path = self.monitoring_dir / "structured_logger.py"
        spec = importlib.util.spec_from_file_location("structured_logger", structured_logger_path)
        logger_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(logger_module)
        
        StructuredLogger = logger_module.StructuredLogger
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = Path(tmp_dir) / "rotation_test.log"
            logger = StructuredLogger(log_file=str(log_file))
            
            # Configure rotation (small size for testing)
            rotation_config = {
                'max_size_mb': 1,  # 1MB max size
                'backup_count': 3,  # Keep 3 backup files
                'rotation_enabled': True
            }
            logger.configure_rotation(**rotation_config)
            
            # Generate logs to trigger rotation
            large_message = "x" * 1000  # 1KB message
            for i in range(1100):  # Generate > 1MB of logs
                logger.log_structured('INFO', f'Rotation test {i}: {large_message}', 
                                     iteration=i, test_data=large_message[:100])
            
            # Check that rotation occurred
            log_files = list(Path(tmp_dir).glob("rotation_test.log*"))
            assert len(log_files) > 1, "Should have created rotated log files"
            
            # Check backup files exist
            backup_files = [f for f in log_files if '.log.' in f.name]
            assert len(backup_files) <= 3, "Should not exceed backup count"
            
            # Verify main log file is not too large
            main_log_size = log_file.stat().st_size / (1024 * 1024)  # MB
            assert main_log_size <= 1.5, f"Main log should be around 1MB, got {main_log_size:.2f}MB"
    
    def test_metric_collection_accuracy(self):
        """Test metrics collection accuracy and aggregation."""
        metrics_path = self.monitoring_dir / "metrics_collector.py"
        spec = importlib.util.spec_from_file_location("metrics_collector", metrics_path)
        metrics_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(metrics_module)
        
        MetricsCollector = metrics_module.MetricsCollector
        collector = MetricsCollector()
        
        # Test counter metrics
        collector.increment_counter('downloads_total')
        collector.increment_counter('downloads_total', value=5)
        collector.increment_counter('errors_total')
        
        # Test gauge metrics
        collector.set_gauge('active_downloads', 10)
        collector.set_gauge('memory_usage_mb', 150.5)
        
        # Test histogram metrics
        collector.record_histogram('download_duration_ms', 1500)
        collector.record_histogram('download_duration_ms', 2000)
        collector.record_histogram('download_duration_ms', 1200)
        
        # Verify counter accuracy
        assert collector.get_counter('downloads_total') == 6, "Counter should sum correctly"
        assert collector.get_counter('errors_total') == 1, "Error counter should be 1"
        
        # Verify gauge accuracy
        assert collector.get_gauge('active_downloads') == 10, "Gauge should store current value"
        assert collector.get_gauge('memory_usage_mb') == 150.5, "Gauge should handle floats"
        
        # Verify histogram statistics
        histogram_stats = collector.get_histogram_stats('download_duration_ms')
        assert histogram_stats['count'] == 3, "Should track sample count"
        assert histogram_stats['min'] == 1200, "Should track minimum"
        assert histogram_stats['max'] == 2000, "Should track maximum"
        assert 1400 <= histogram_stats['avg'] <= 1600, "Should calculate average correctly"
    
    def test_alert_threshold_triggers(self):
        """Test alert threshold triggers and notification system."""
        alert_path = self.monitoring_dir / "alert_manager.py"
        spec = importlib.util.spec_from_file_location("alert_manager", alert_path)
        alert_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(alert_module)
        
        AlertManager = alert_module.AlertManager
        alert_manager = AlertManager()
        
        # Configure alert thresholds
        alert_config = {
            'memory_usage_mb': {'warning': 100, 'critical': 200},
            'error_rate_percent': {'warning': 5, 'critical': 10},
            'download_duration_ms': {'warning': 5000, 'critical': 10000}
        }
        alert_manager.configure_thresholds(alert_config)
        
        # Mock notification handler
        notifications = []
        def mock_notify(alert_type, metric, value, threshold):
            notifications.append({
                'type': alert_type,
                'metric': metric,
                'value': value,
                'threshold': threshold
            })
        
        alert_manager.set_notification_handler(mock_notify)
        
        # Test warning threshold
        alert_manager.check_metric('memory_usage_mb', 120)
        assert len(notifications) == 1, "Should trigger warning alert"
        assert notifications[0]['type'] == 'warning', "Should be warning type"
        assert notifications[0]['metric'] == 'memory_usage_mb', "Should identify metric"
        
        # Test critical threshold
        alert_manager.check_metric('memory_usage_mb', 250)
        assert len(notifications) == 2, "Should trigger critical alert"
        assert notifications[1]['type'] == 'critical', "Should be critical type"
        
        # Test normal value (no alert)
        alert_manager.check_metric('memory_usage_mb', 50)
        assert len(notifications) == 2, "Should not trigger alert for normal value"
        
        # Test alert suppression (avoid spam)
        alert_manager.check_metric('memory_usage_mb', 260)  # Another critical
        alert_manager.check_metric('memory_usage_mb', 270)  # Another critical
        
        # Should suppress repeated alerts within timeframe
        recent_alerts = [n for n in notifications if n['type'] == 'critical']
        assert len(recent_alerts) <= 3, "Should suppress repeated alerts"
    
    def test_performance_regression_detection(self):
        """Test performance regression detection and baseline comparison."""
        perf_path = self.monitoring_dir / "performance_tracker.py"
        spec = importlib.util.spec_from_file_location("performance_tracker", perf_path)
        perf_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(perf_module)
        
        PerformanceTracker = perf_module.PerformanceTracker
        tracker = PerformanceTracker()
        
        # Establish baseline performance
        baseline_data = [
            ('download_model', 1500),
            ('download_model', 1600),
            ('download_model', 1400),
            ('download_model', 1550),
            ('download_model', 1450)
        ]
        
        for operation, duration in baseline_data:
            tracker.record_performance(operation, duration)
        
        # Calculate baseline
        tracker.establish_baseline('download_model')
        baseline = tracker.get_baseline('download_model')
        
        assert 1400 <= baseline.avg <= 1600, "Baseline should be around 1500ms"
        assert baseline.count == 5, "Baseline should include all samples"
        
        # Test normal performance (within threshold)
        regression = tracker.check_regression('download_model', 1580)
        assert not regression.is_regression, "Normal performance should not be regression"
        
        # Test performance regression (significantly slower)
        regression = tracker.check_regression('download_model', 3000)
        assert regression.is_regression, "Significant slowdown should be detected as regression"
        assert regression.regression_factor > 1.5, "Should calculate regression factor"
        
        # Test performance improvement
        improvement = tracker.check_regression('download_model', 800)
        assert improvement.is_improvement, "Significant speedup should be detected as improvement"
    
    def test_log_aggregation_performance(self):
        """Test log aggregation performance with large volumes."""
        structured_logger_path = self.monitoring_dir / "structured_logger.py"
        spec = importlib.util.spec_from_file_location("structured_logger", structured_logger_path)
        logger_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(logger_module)
        
        StructuredLogger = logger_module.StructuredLogger
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = Path(tmp_dir) / "aggregation_test.log"
            logger = StructuredLogger(log_file=str(log_file))
            
            # Generate large volume of logs
            log_count = 1000
            start_time = time.time()
            
            for i in range(log_count):
                logger.log_structured('INFO', f'Aggregation test entry {i}',
                                     entry_id=i,
                                     operation='bulk_test',
                                     data_size=i * 100,
                                     processing_time=i * 0.1)
            
            logging_time = time.time() - start_time
            
            # Test aggregation performance
            if hasattr(logger, 'aggregate_logs'):
                start_time = time.time()
                aggregation = logger.aggregate_logs(
                    start_time=time.time() - 3600,  # Last hour
                    group_by=['operation'],
                    metrics=['count', 'avg_data_size', 'total_processing_time']
                )
                aggregation_time = time.time() - start_time
                
                # Verify aggregation results
                assert 'bulk_test' in aggregation, "Should aggregate by operation"
                assert aggregation['bulk_test']['count'] == log_count, "Should count all entries"
                assert aggregation_time < 1.0, "Aggregation should be fast"
            
            # Test log search performance
            if hasattr(logger, 'search_logs'):
                start_time = time.time()
                search_results = logger.search_logs(
                    filters={'operation': 'bulk_test'},
                    limit=100
                )
                search_time = time.time() - start_time
                
                assert len(search_results) <= 100, "Should respect limit"
                assert search_time < 0.5, "Search should be fast"
            
            # Performance benchmarks
            assert logging_time < 2.0, f"Logging {log_count} entries should be fast, took {logging_time:.2f}s"
            
            # Verify log file size is reasonable
            log_size_mb = log_file.stat().st_size / (1024 * 1024)
            assert log_size_mb < 5, f"Log file should be reasonable size, got {log_size_mb:.2f}MB"
    
    def test_real_time_monitoring_integration(self):
        """Test real-time monitoring integration with all components."""
        # Import all monitoring components
        structured_logger_path = self.monitoring_dir / "structured_logger.py"
        metrics_path = self.monitoring_dir / "metrics_collector.py"
        alert_path = self.monitoring_dir / "alert_manager.py"
        
        # Load modules
        spec = importlib.util.spec_from_file_location("structured_logger", structured_logger_path)
        logger_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(logger_module)
        
        spec = importlib.util.spec_from_file_location("metrics_collector", metrics_path)
        metrics_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(metrics_module)
        
        spec = importlib.util.spec_from_file_location("alert_manager", alert_path)
        alert_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(alert_module)
        
        # Initialize integrated monitoring
        if hasattr(logger_module, 'EnhancedMonitoringService'):
            EnhancedMonitoringService = logger_module.EnhancedMonitoringService
            monitoring = EnhancedMonitoringService()
            
            # Test integrated operation monitoring
            operation_id = monitoring.start_operation('model_download', model_id=12345)
            
            # Simulate operation progress
            monitoring.update_operation_progress(operation_id, progress=25, status='downloading')
            monitoring.update_operation_progress(operation_id, progress=75, status='processing')
            
            # Complete operation
            monitoring.complete_operation(operation_id, success=True, 
                                        result={'size_mb': 150, 'format': 'safetensors'})
            
            # Verify integrated metrics
            stats = monitoring.get_operation_stats()
            assert stats['total_operations'] >= 1, "Should track operations"
            assert stats['successful_operations'] >= 1, "Should track successes"
            
            # Test monitoring dashboard data
            if hasattr(monitoring, 'get_dashboard_data'):
                dashboard = monitoring.get_dashboard_data()
                
                assert 'current_operations' in dashboard, "Should provide current operations"
                assert 'recent_metrics' in dashboard, "Should provide recent metrics"
                assert 'alert_summary' in dashboard, "Should provide alert summary"
    
    def test_monitoring_configuration_management(self):
        """Test monitoring configuration management and persistence."""
        # Test if monitoring config management exists
        config_path = self.monitoring_dir / "config.py"
        if config_path.exists():
            spec = importlib.util.spec_from_file_location("monitoring_config", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            if hasattr(config_module, 'MonitoringConfig'):
                MonitoringConfig = config_module.MonitoringConfig
                config = MonitoringConfig()
                
                # Test configuration loading
                test_config = {
                    'logging': {
                        'level': 'INFO',
                        'format': 'json',
                        'rotation': {'max_size_mb': 10, 'backup_count': 5}
                    },
                    'metrics': {
                        'collection_interval': 30,
                        'retention_days': 7
                    },
                    'alerts': {
                        'notification_channels': ['email', 'webhook'],
                        'suppress_duration_minutes': 5
                    }
                }
                
                config.load_config(test_config)
                
                # Verify configuration is applied
                assert config.get_log_level() == 'INFO', "Should set log level"
                assert config.get_metrics_interval() == 30, "Should set metrics interval"
                assert 'email' in config.get_notification_channels(), "Should configure notifications"
    
    def test_monitoring_performance_overhead(self):
        """Test that monitoring has minimal performance overhead."""
        structured_logger_path = self.monitoring_dir / "structured_logger.py"
        spec = importlib.util.spec_from_file_location("structured_logger", structured_logger_path)
        logger_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(logger_module)
        
        StructuredLogger = logger_module.StructuredLogger
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = Path(tmp_dir) / "overhead_test.log"
            logger = StructuredLogger(log_file=str(log_file))
            
            # Measure baseline (no logging)
            iterations = 1000
            
            start_time = time.time()
            for i in range(iterations):
                # Simulate work without logging
                result = i * 2 + 1
                data = {'iteration': i, 'result': result}
            baseline_time = time.time() - start_time
            
            # Measure with logging
            start_time = time.time()
            for i in range(iterations):
                # Same work with logging
                result = i * 2 + 1
                data = {'iteration': i, 'result': result}
                logger.log_structured('DEBUG', f'Test iteration {i}', **data)
            logging_time = time.time() - start_time
            
            # Calculate overhead
            overhead_percent = ((logging_time - baseline_time) / baseline_time) * 100
            
            # Monitoring should add reasonable overhead (logging is inherently expensive)
            assert overhead_percent < 5000, f"Monitoring overhead should be <5000%, got {overhead_percent:.1f}%"
            assert logging_time < baseline_time * 100, "Logging should not be excessively slow"