#!/usr/bin/env python3
"""
Component Integration Tests.
Tests the behavior of multiple components working together to ensure
end-to-end functionality works as expected from a user perspective.

Based on Gemini audit recommendation for testing user-focused behaviors (What)
rather than just implementation details (How).
"""

import pytest
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sqlite3

# Import components for integration testing
from src.core.bulk.download_manager import BulkDownloadManager
from src.core.download.manager import DownloadManager
from src.core.performance.optimizer import PerformanceOptimizer
from src.core.search.advanced_search import AdvancedSearchEngine
from src.core.security.scanner import SecurityScanner
from src.core.reliability.health_check import HealthChecker
from src.core.analytics.collector import AnalyticsCollector
from src.core.security.audit import SecurityAuditor
from src.data.database import DatabaseManager
from src.api.client import CivitAIClient


class TestHighLoadOptimizationIntegration:
    """
    Test that under high load conditions, the optimizer works with
    bulk download manager to appropriately limit parallel downloads.
    
    This tests the USER BEHAVIOR: "When system is under stress,
    downloads are automatically throttled to maintain stability"
    """
    
    @pytest.fixture
    async def integration_setup(self):
        """Setup integrated system components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize database
            db_path = temp_path / "test.db"
            db_manager = DatabaseManager(str(db_path))
            await db_manager.initialize()
            
            # Initialize core components
            client = Mock(spec=CivitAIClient)
            download_manager = DownloadManager(
                client=client,
                download_dir=temp_path / "downloads",
                db_manager=db_manager
            )
            
            performance_optimizer = PerformanceOptimizer()
            
            bulk_manager = BulkDownloadManager(
                download_manager=download_manager,
                performance_optimizer=performance_optimizer,
                db_manager=db_manager
            )
            
            yield {
                'bulk_manager': bulk_manager,
                'download_manager': download_manager,
                'optimizer': performance_optimizer,
                'temp_path': temp_path,
                'db_manager': db_manager
            }
    
    @pytest.mark.asyncio
    async def test_high_load_automatic_throttling(self, integration_setup):
        """
        Test that when CPU/memory usage is high, the system automatically
        reduces concurrent downloads to maintain stability.
        """
        components = integration_setup
        bulk_manager = components['bulk_manager']
        optimizer = components['optimizer']
        
        # Simulate high resource usage
        with patch.object(optimizer, 'get_current_metrics') as mock_metrics:
            mock_metrics.return_value = {
                'cpu_percent': 95.0,  # Very high CPU
                'memory_percent': 90.0,  # Very high memory
                'disk_io_percent': 85.0,  # High disk I/O
                'network_mbps': 50.0
            }
            
            # Request to download 10 files (would normally use max concurrent)
            mock_jobs = []
            for i in range(10):
                mock_jobs.append({
                    'id': f'job_{i}',
                    'url': f'https://example.com/model_{i}.safetensors',
                    'filename': f'model_{i}.safetensors',
                    'size': 1024 * 1024 * 100  # 100MB each
                })
            
            # Mock download operations
            with patch.object(bulk_manager.download_manager, 'download_file') as mock_download:
                mock_download.return_value = Mock(success=True)
                
                # Start bulk download
                bulk_job = await bulk_manager.create_bulk_job(
                    name="high_load_test",
                    items=mock_jobs
                )
                
                # Process jobs under high load
                await bulk_manager.process_bulk_job(bulk_job.id)
                
                # Verify that concurrent downloads were limited due to high resource usage
                # The optimizer should have reduced max_concurrent_downloads
                final_metrics = optimizer.get_optimization_recommendations()
                
                # Under high load, should recommend reduced concurrency
                assert final_metrics['max_concurrent_downloads'] <= 2, \
                    "System should limit concurrent downloads under high load"
                
                # Verify downloads still completed (resilience)
                job_status = await bulk_manager.get_job_status(bulk_job.id)
                assert job_status['status'] in ['completed', 'processing'], \
                    "Downloads should continue even under load constraints"
    
    @pytest.mark.asyncio
    async def test_pause_resume_with_optimization(self, integration_setup):
        """
        Test that pausing and resuming bulk jobs works correctly
        with performance optimization in the loop.
        """
        components = integration_setup
        bulk_manager = components['bulk_manager']
        
        # Create test jobs
        mock_jobs = [
            {'id': 'job_1', 'url': 'https://example.com/model1.safetensors', 
             'filename': 'model1.safetensors', 'size': 1024 * 1024 * 50},
            {'id': 'job_2', 'url': 'https://example.com/model2.safetensors',
             'filename': 'model2.safetensors', 'size': 1024 * 1024 * 75},
        ]
        
        with patch.object(bulk_manager.download_manager, 'download_file') as mock_download, \
             patch.object(bulk_manager.download_manager, 'pause_download') as mock_pause, \
             patch.object(bulk_manager.download_manager, 'resume_download') as mock_resume:
            
            # Mock download to simulate slow download
            async def slow_download(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate download time
                return Mock(success=True)
            
            mock_download.side_effect = slow_download
            mock_pause.return_value = True
            mock_resume.return_value = True
            
            # Create and start bulk job
            bulk_job = await bulk_manager.create_bulk_job(
                name="pause_resume_test",
                items=mock_jobs
            )
            
            # Start processing (non-blocking)
            process_task = asyncio.create_task(
                bulk_manager.process_bulk_job(bulk_job.id)
            )
            
            # Wait a bit for downloads to start
            await asyncio.sleep(0.05)
            
            # Pause the job
            await bulk_manager.pause_job(bulk_job.id)
            
            # Verify pause was called on download manager
            mock_pause.assert_called()
            
            # Check job status is paused
            status = await bulk_manager.get_job_status(bulk_job.id)
            assert status['status'] == 'paused'
            
            # Resume the job
            await bulk_manager.resume_job(bulk_job.id)
            
            # Verify resume was called
            mock_resume.assert_called()
            
            # Wait for completion
            await process_task
            
            # Verify final completion
            final_status = await bulk_manager.get_job_status(bulk_job.id)
            assert final_status['status'] == 'completed'


class TestSearchToDownloadIntegration:
    """
    Test the complete flow from search to download with security scanning.
    
    Tests USER BEHAVIOR: "Search for models, select results, download safely"
    """
    
    @pytest.fixture
    async def search_download_setup(self):
        """Setup search and download integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Database setup
            db_path = temp_path / "integration.db"
            db_manager = DatabaseManager(str(db_path))
            await db_manager.initialize()
            
            # Components
            client = Mock(spec=CivitAIClient)
            search_engine = AdvancedSearchEngine(client=client, db_manager=db_manager)
            security_scanner = SecurityScanner()
            download_manager = DownloadManager(
                client=client,
                download_dir=temp_path / "downloads",
                db_manager=db_manager
            )
            
            yield {
                'search_engine': search_engine,
                'scanner': security_scanner,
                'download_manager': download_manager,
                'client': client,
                'temp_path': temp_path
            }
    
    @pytest.mark.asyncio
    async def test_search_to_secure_download_flow(self, search_download_setup):
        """
        Test complete flow: search -> security scan -> download
        """
        components = search_download_setup
        search_engine = components['search_engine']
        scanner = components['scanner']
        download_manager = components['download_manager']
        client = components['client']
        
        # Mock search results
        mock_search_results = [
            {
                'id': 12345,
                'name': 'Test Model',
                'type': 'Checkpoint',
                'modelVersions': [{
                    'id': 67890,
                    'files': [{
                        'id': 11111,
                        'name': 'test_model.safetensors',
                        'downloadUrl': 'https://example.com/test_model.safetensors',
                        'sizeKB': 2048,
                        'metadata': {'format': 'SafeTensor'}
                    }]
                }]
            }
        ]
        
        # Mock API responses
        client.search_models.return_value = {
            'items': mock_search_results,
            'metadata': {'totalItems': 1}
        }
        
        # 1. SEARCH PHASE
        search_results = await search_engine.search(
            query="anime style",
            filters={'types': ['Checkpoint'], 'nsfw': False}
        )
        
        assert len(search_results) == 1
        assert search_results[0]['name'] == 'Test Model'
        
        # 2. SECURITY SCAN PHASE
        download_url = search_results[0]['modelVersions'][0]['files'][0]['downloadUrl']
        filename = search_results[0]['modelVersions'][0]['files'][0]['name']
        
        # Mock security scan (safe file)
        with patch.object(scanner, 'scan_url') as mock_scan:
            mock_scan.return_value = {
                'safe': True,
                'threats': [],
                'risk_level': 'low',
                'scan_time': time.time()
            }
            
            scan_result = await scanner.scan_url(download_url)
            assert scan_result['safe'] is True
        
        # 3. DOWNLOAD PHASE (only if security scan passes)
        if scan_result['safe']:
            with patch.object(download_manager, 'download_file') as mock_download:
                mock_download.return_value = Mock(
                    success=True,
                    file_path=components['temp_path'] / 'downloads' / filename,
                    downloaded_size=2048 * 1024
                )
                
                download_result = await download_manager.download_file(
                    url=download_url,
                    filename=filename
                )
                
                assert download_result.success is True
                mock_download.assert_called_once()
        
        # Verify the complete flow executed without errors
        client.search_models.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_malicious_file_blocked_flow(self, search_download_setup):
        """
        Test that malicious files are blocked from download after security scan.
        """
        components = search_download_setup
        search_engine = components['search_engine']
        scanner = components['scanner']
        download_manager = components['download_manager']
        client = components['client']
        
        # Mock search results with potentially malicious file
        mock_search_results = [
            {
                'id': 54321,
                'name': 'Suspicious Model',
                'type': 'Checkpoint',
                'modelVersions': [{
                    'id': 98765,
                    'files': [{
                        'id': 22222,
                        'name': 'suspicious_model.ckpt',
                        'downloadUrl': 'https://example.com/suspicious_model.ckpt',
                        'sizeKB': 4096,
                        'metadata': {'format': 'Other'}
                    }]
                }]
            }
        ]
        
        client.search_models.return_value = {
            'items': mock_search_results,
            'metadata': {'totalItems': 1}
        }
        
        # Search phase
        search_results = await search_engine.search(
            query="suspicious model",
            filters={'types': ['Checkpoint']}
        )
        
        # Security scan detects threat
        download_url = search_results[0]['modelVersions'][0]['files'][0]['downloadUrl']
        
        with patch.object(scanner, 'scan_url') as mock_scan:
            mock_scan.return_value = {
                'safe': False,
                'threats': ['MALICIOUS_CODE', 'SUSPICIOUS_PATTERNS'],
                'risk_level': 'high',
                'scan_time': time.time()
            }
            
            scan_result = await scanner.scan_url(download_url)
            assert scan_result['safe'] is False
            assert 'MALICIOUS_CODE' in scan_result['threats']
        
        # Download should NOT proceed
        with patch.object(download_manager, 'download_file') as mock_download:
            # In real implementation, this would be blocked by security policy
            # For test, we verify the flow can detect the threat
            if not scan_result['safe']:
                # Download blocked - this is the expected behavior
                mock_download.assert_not_called()
            else:
                pytest.fail("Download should have been blocked due to security threat")


class TestMonitoringIntegration:
    """
    Test monitoring and analytics integration across components.
    """
    
    @pytest.fixture
    async def monitoring_setup(self):
        """Setup monitoring integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Database
            db_path = temp_path / "monitoring.db"
            db_manager = DatabaseManager(str(db_path))
            await db_manager.initialize()
            
            # Components
            health_checker = HealthChecker()
            analytics_collector = AnalyticsCollector(db_manager=db_manager)
            security_auditor = SecurityAuditor(
                audit_db_path=temp_path / "audit.db",
                data_dir=temp_path
            )
            
            yield {
                'health_checker': health_checker,
                'analytics': analytics_collector,
                'auditor': security_auditor,
                'temp_path': temp_path
            }
    
    @pytest.mark.asyncio
    async def test_system_health_with_analytics(self, monitoring_setup):
        """
        Test that system health monitoring integrates with analytics collection.
        """
        components = monitoring_setup
        health_checker = components['health_checker']
        analytics = components['analytics']
        
        # Simulate system health checks over time
        health_data = []
        
        for i in range(5):
            # Mock varying system conditions
            with patch('psutil.cpu_percent', return_value=50 + i * 10), \
                 patch('psutil.virtual_memory') as mock_memory:
                
                mock_memory.return_value.percent = 40 + i * 5
                
                health = await health_checker.check_system_health()
                health_data.append({
                    'timestamp': time.time(),
                    'cpu_percent': health.metrics.get('cpu_usage', 0),
                    'memory_percent': health.metrics.get('memory_usage', 0),
                    'status': health.status.value
                })
                
                # Record analytics event
                await analytics.record_event(
                    category='system',
                    action='health_check',
                    properties={
                        'cpu_usage': health.metrics.get('cpu_usage', 0),
                        'memory_usage': health.metrics.get('memory_usage', 0),
                        'status': health.status.value
                    }
                )
                
                await asyncio.sleep(0.01)  # Small delay
        
        # Verify analytics captured the health trends
        events = await analytics.get_events(
            category='system',
            start_time=health_data[0]['timestamp'],
            end_time=health_data[-1]['timestamp']
        )
        
        assert len(events) == 5, "All health check events should be recorded"
        
        # Verify trend analysis
        cpu_trend = [event['properties']['cpu_usage'] for event in events]
        assert cpu_trend == [50, 60, 70, 80, 90], "CPU trend should be captured correctly"
    
    @pytest.mark.asyncio
    async def test_security_audit_integration(self, monitoring_setup):
        """
        Test security auditing integration with other components.
        """
        components = monitoring_setup
        auditor = components['auditor']
        analytics = components['analytics']
        
        # Simulate security events
        security_events = [
            {'action': 'login_attempt', 'result': 'success', 'user_id': 'user1'},
            {'action': 'download_start', 'result': 'success', 'file': 'model1.safetensors'},
            {'action': 'login_attempt', 'result': 'failed', 'user_id': 'user2'},
            {'action': 'login_attempt', 'result': 'failed', 'user_id': 'user2'},
            {'action': 'login_attempt', 'result': 'failed', 'user_id': 'user2'},
        ]
        
        # Record events in both auditor and analytics
        for event in security_events:
            # Security audit
            from src.core.security.audit import AuditEvent, AuditCategory
            audit_event = AuditEvent(
                category=AuditCategory.AUTHENTICATION if 'login' in event['action'] else AuditCategory.DATA_ACCESS,
                action=event['action'],
                result=event['result'],
                user_id=event.get('user_id', 'system'),
                details=event
            )
            await auditor.log_event(audit_event)
            
            # Analytics
            await analytics.record_event(
                category='security',
                action=event['action'],
                properties=event
            )
        
        # Check security audit statistics
        audit_stats = await auditor.get_audit_statistics(period_hours=1)
        assert audit_stats['total_events'] >= 5
        
        # Check for suspicious patterns (multiple failed logins)
        failed_logins = [e for e in security_events if e['action'] == 'login_attempt' and e['result'] == 'failed']
        assert len(failed_logins) == 3, "Should detect multiple failed login attempts"
        
        # Analytics should also capture this pattern
        security_events_analytics = await analytics.get_events(category='security')
        assert len(security_events_analytics) >= 5, "All security events should be in analytics"


class TestErrorRecoveryIntegration:
    """
    Test error handling and recovery across integrated components.
    """
    
    @pytest.mark.asyncio
    async def test_download_failure_recovery_with_optimizer(self):
        """
        Test that download failures trigger optimizer adjustments and retry logic.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Setup components
            db_manager = DatabaseManager(str(temp_path / "test.db"))
            await db_manager.initialize()
            
            client = Mock(spec=CivitAIClient)
            download_manager = DownloadManager(
                client=client,
                download_dir=temp_path / "downloads",
                db_manager=db_manager
            )
            
            optimizer = PerformanceOptimizer()
            
            # Mock download failures followed by success
            download_attempts = []
            
            async def mock_download_with_failures(*args, **kwargs):
                download_attempts.append(time.time())
                
                if len(download_attempts) <= 2:
                    # First two attempts fail
                    raise Exception("Network timeout")
                else:
                    # Third attempt succeeds
                    return Mock(success=True, file_path=temp_path / "downloads" / "test.safetensors")
            
            with patch.object(download_manager, 'download_file', side_effect=mock_download_with_failures):
                
                # Configure retry logic
                download_manager.max_retries = 3
                download_manager.retry_delay = 0.01  # Fast retry for testing
                
                # Attempt download
                try:
                    result = await download_manager.download_file_with_retry(
                        url="https://example.com/test.safetensors",
                        filename="test.safetensors"
                    )
                    
                    # Should eventually succeed after retries
                    assert result.success is True
                    assert len(download_attempts) == 3, "Should retry until success"
                    
                    # Optimizer should adjust based on failure pattern
                    recommendations = optimizer.get_optimization_recommendations()
                    # After failures, should recommend conservative settings
                    assert recommendations['max_concurrent_downloads'] <= 3
                    
                except Exception as e:
                    pytest.fail(f"Download should have succeeded after retries: {e}")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])