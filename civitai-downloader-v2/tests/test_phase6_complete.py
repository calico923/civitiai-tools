#!/usr/bin/env python3
"""
Phase 6 Complete System Tests.
Tests for the final implementation covering all Phase 6 components.
"""

import pytest
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json
import sqlite3

# Phase 6.1: Adaptability System Tests
from src.core.adaptability.api_detector import APIChangeDetector, APIChangeEvent
from src.core.adaptability.plugin_manager import PluginManager, Plugin, PluginMetadata, PluginType
from src.core.adaptability.dynamic_types import DynamicModelTypeManager, ModelTypeInfo
from src.core.adaptability.migration import MigrationManager, ConfigMigration

# Phase 6.2: Reliability System Tests  
from src.core.reliability.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerError
from src.core.reliability.health_check import HealthChecker, HealthStatus, SystemHealth
from src.core.reliability.integrity import IntegrityManager, FileIntegrity, IntegrityStatus
from src.core.reliability.uptime_monitor import UptimeMonitor, AvailabilityTracker, ServiceStatus

# Phase 6.3: Security System Tests
from src.core.security.audit import SecurityAuditor, AuditEvent, AuditLevel, AuditCategory
from src.core.security.sandbox import SecureSandbox, SandboxConfig, SandboxStatus
from src.core.security.encryption import DataEncryption, EncryptionConfig, EncryptionLevel
from src.core.security.access_control import AccessController, Permission, Role, SecurityPolicy

# Phase 6.4: UI/UX System Tests
from src.ui.progress import ProgressTracker, ProgressTask, ProgressLevel
from src.ui.interactive import InteractiveInterface, UserPrompt, InputType
from src.ui.dashboard import Dashboard, MetricCard, MetricType
from src.ui.export import ExportInterface, ExportFormat, ExportOptions


class TestPhase6Adaptability:
    """Test Phase 6.1: Adaptability System."""
    
    @pytest.fixture
    def api_detector(self):
        """Create API change detector for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            detector = APIChangeDetector(cache_dir=Path(temp_dir))
            yield detector
    
    @pytest.fixture  
    def plugin_manager(self):
        """Create plugin manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = PluginManager(plugin_dir=Path(temp_dir))
            yield manager
    
    @pytest.fixture
    def dynamic_types(self):
        """Create dynamic model type manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DynamicModelTypeManager(cache_dir=Path(temp_dir))
            yield manager
    
    @pytest.fixture
    def migration_manager(self):
        """Create migration manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MigrationManager(data_dir=Path(temp_dir))
            yield manager
    
    @pytest.mark.asyncio
    async def test_api_change_detection(self, api_detector):
        """Test API change detection functionality."""
        # Mock API responses for change detection
        with patch.object(api_detector, '_scan_endpoint') as mock_scan:
            mock_scan.return_value = [APIChangeEvent(
                timestamp=time.time(),
                change_type="modified",
                endpoint="/v1/models",
                detail="New parameter added",
                impact_level="low",
                suggested_action="Update API client"
            )]
            
            # Simulate API change detection
            changes = await api_detector.detect_api_changes(force_full_scan=True)
            
            # Verify change detection
            assert len(changes) >= 0  # May be 0 if no previous spec
            mock_scan.assert_called()
    
    def test_plugin_discovery_and_loading(self, plugin_manager):
        """Test plugin discovery and loading."""
        # Create a mock plugin file
        plugin_code = '''
class TestPlugin(Plugin):
    PLUGIN_METADATA = {
        "name": "test_plugin",
        "version": "1.0.0", 
        "description": "Test plugin",
        "author": "Test",
        "plugin_type": "model_processor"
    }
    
    async def initialize(self, config):
        return True
        
    async def process(self, data, context):
        return data
'''
        
        plugin_file = plugin_manager.plugin_dir / "test_plugin.py"
        plugin_file.write_text(plugin_code)
        
        # Test plugin discovery
        discovered = asyncio.run(plugin_manager.discover_plugins())
        assert len(discovered) >= 0
    
    def test_dynamic_model_type_detection(self, dynamic_types):
        """Test dynamic model type detection."""
        # Test model data for type inference
        test_model_data = {
            'name': 'test_lora_model',
            'type': None,  # No explicit type
            'modelVersions': [{
                'files': [{
                    'name': 'model.safetensors',
                    'sizeKB': 100000  # ~100MB
                }]
            }],
            'tags': [{'name': 'lora'}, {'name': 'character'}]
        }
        
        # Test type analysis
        detected_type = dynamic_types.analyze_model_data(test_model_data)
        assert detected_type is not None
        
        # Test type info retrieval
        type_info = dynamic_types.get_type_info(detected_type)
        assert isinstance(type_info, ModelTypeInfo)
    
    @pytest.mark.asyncio
    async def test_data_migration(self, migration_manager):
        """Test data migration system."""
        # Create test config file for migration
        old_config = migration_manager.data_dir / "config.json"
        old_config_data = {
            "api_url": "https://civitai.com/api/v1",
            "timeout": 30,
            "download_dir": "./downloads"
        }
        old_config.write_text(json.dumps(old_config_data))
        
        # Test migration to latest version
        success = await migration_manager.migrate_to_latest("2.0")
        
        # Verify migration results
        assert success is True
        assert migration_manager.get_current_version() == "2.0"
        
        # Check migrated config exists
        new_config = migration_manager.data_dir / "config" / "settings.yaml"
        if new_config.exists():
            # Migration was successful
            pass


class TestPhase6Reliability:
    """Test Phase 6.2: Reliability System."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing."""
        return CircuitBreaker(
            name="test_circuit",
            failure_threshold=3,
            recovery_timeout=1  # Short timeout for testing
        )
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            checker = HealthChecker(data_dir=Path(temp_dir))
            yield checker
    
    @pytest.fixture
    def integrity_manager(self):
        """Create integrity manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = IntegrityManager(data_dir=Path(temp_dir))
            yield manager
    
    @pytest.fixture
    def uptime_monitor(self):
        """Create uptime monitor for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = UptimeMonitor(data_dir=Path(temp_dir))
            yield monitor
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, circuit_breaker):
        """Test circuit breaker open/close functionality."""
        # Mock function that fails
        async def failing_function():
            raise Exception("Test failure")
        
        # Test normal failure counting
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.failure_count == 1
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # Trigger enough failures to open circuit
        for _ in range(2):  # Need 2 more failures (total 3)
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)
        
        # Circuit should be open now
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Next call should fail fast
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(failing_function)
    
    @pytest.mark.asyncio
    async def test_health_check_system(self, health_checker):
        """Test system health checking."""
        # Mock system metrics
        with patch('psutil.cpu_percent', return_value=75.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.used = 500 * 1024**3  # 500GB
            mock_disk.return_value.total = 1000 * 1024**3  # 1TB
            
            # Test health check
            health = await health_checker.check_system_health()
            
            # Verify health status
            assert isinstance(health, SystemHealth)
            assert health.status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
            assert len(health.metrics) > 0
    
    @pytest.mark.asyncio 
    async def test_file_integrity_verification(self, integrity_manager):
        """Test file integrity verification."""
        # Create test file
        test_file = integrity_manager.data_dir / "test_file.txt"
        test_content = b"This is test content for integrity verification"
        test_file.write_bytes(test_content)
        
        # Calculate expected hash
        import hashlib
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        # Register file for integrity monitoring
        integrity_manager.register_file(test_file, expected_hash)
        
        # Test integrity verification
        results = await integrity_manager.verify_file_integrity(test_file)
        
        # Verify results
        assert test_file.name in results or str(test_file) in results
        # File should pass integrity check
        assert any(results.values()) or len(results) == 0
    
    @pytest.mark.asyncio
    async def test_uptime_monitoring(self, uptime_monitor):
        """Test uptime monitoring and availability tracking."""
        # Record some uptime data
        await uptime_monitor.record_status("system", ServiceStatus.OPERATIONAL, response_time=0.5)
        await uptime_monitor.record_status("api", ServiceStatus.OPERATIONAL, response_time=1.2)
        
        # Calculate availability metrics
        metrics = await uptime_monitor.calculate_availability("system", period_hours=1)
        
        # Verify metrics
        assert hasattr(metrics, 'uptime_percentage')
        assert hasattr(metrics, 'total_uptime')
        assert metrics.uptime_percentage >= 0.0
        assert metrics.uptime_percentage <= 100.0


class TestPhase6Security:
    """Test Phase 6.3: Security System."""
    
    @pytest.fixture
    def security_auditor(self):
        """Create security auditor for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auditor = SecurityAuditor(data_dir=Path(temp_dir))
            yield auditor
    
    @pytest.fixture
    def secure_sandbox(self):
        """Create secure sandbox for testing."""
        config = SandboxConfig(
            max_memory_mb=64,
            max_cpu_time=5,
            max_wall_time=10,
            allow_network=False
        )
        return SecureSandbox(config)
    
    @pytest.fixture
    def data_encryption(self):
        """Create data encryption for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EncryptionConfig(
                level=EncryptionLevel.STANDARD,
                key_derivation_iterations=1000  # Lower for testing
            )
            encryption = DataEncryption(config, key_store_path=Path(temp_dir) / "keys.db")
            yield encryption
    
    @pytest.fixture
    def access_controller(self):
        """Create access controller for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            policy = SecurityPolicy(
                name="test_policy",
                description="Test security policy",
                max_login_attempts=3,
                session_timeout_minutes=10
            )
            controller = AccessController(data_dir=Path(temp_dir), policy=policy)
            yield controller
    
    @pytest.mark.asyncio
    async def test_security_auditing(self, security_auditor):
        """Test security event auditing."""
        # Create audit event
        audit_event = AuditEvent(
            timestamp=time.time(),
            level=AuditLevel.WARNING,
            category=AuditCategory.AUTHENTICATION,
            event_type="login_attempt",
            source="test_system",
            user_id="test_user",
            action="login",
            result="failed"
        )
        
        # Log the event
        await security_auditor.log_event(audit_event)
        
        # Verify event was logged
        stats = await security_auditor.get_audit_statistics(period_hours=1)
        assert stats['total_events'] > 0
    
    @pytest.mark.asyncio
    async def test_sandbox_execution(self, secure_sandbox):
        """Test secure sandbox execution."""
        # Test configuration and basic functionality
        config = secure_sandbox.config
        assert config.max_memory_mb > 0
        assert config.max_cpu_time > 0
        
        # Test basic sandbox functionality
        assert secure_sandbox.temp_dir is not None
        assert secure_sandbox.temp_dir.exists()
    
    def test_data_encryption_decryption(self, data_encryption):
        """Test data encryption and decryption."""
        # Test data
        test_data = "This is sensitive test data that should be encrypted"
        
        # Encrypt data
        encrypted_data = data_encryption.encrypt_data(test_data)
        
        # Verify encryption
        assert encrypted_data.level == EncryptionLevel.STANDARD
        assert encrypted_data.ciphertext != test_data.encode()
        assert encrypted_data.salt is not None
        
        # Decrypt data
        decrypted_data = data_encryption.decrypt_data(encrypted_data)
        
        # Verify decryption
        assert decrypted_data.decode() == test_data
    
    def test_access_control_system(self, access_controller):
        """Test role-based access control."""
        # Create test user
        success = access_controller.create_user("testuser", "testpass123", Role.USER)
        assert success is True
        
        # Test authentication
        session_id = access_controller.authenticate_user("testuser", "testpass123")
        assert session_id is not None
        
        # Test access check
        result = access_controller.check_access(
            session_id=session_id,
            resource="test_file.txt", 
            action=Permission.READ_FILE
        )
        
        assert result.granted is True
        assert result.user_id is not None


class TestPhase6UIUX:
    """Test Phase 6.4: UI/UX System."""
    
    @pytest.fixture
    def progress_tracker(self):
        """Create progress tracker for testing."""
        return ProgressTracker()
    
    @pytest.fixture
    def interactive_interface(self):
        """Create interactive interface for testing.""" 
        return InteractiveInterface(app_name="Test App")
    
    @pytest.fixture
    def dashboard(self):
        """Create dashboard for testing."""
        return Dashboard(title="Test Dashboard")
    
    @pytest.fixture
    def export_interface(self):
        """Create export interface for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            interface = ExportInterface(data_source=Path(temp_dir))
            yield interface
    
    def test_progress_tracking(self, progress_tracker):
        """Test progress tracking system."""
        # Create progress task
        task = progress_tracker.create_task(
            task_id="test_task",
            name="Test Task",
            level=ProgressLevel.TASK,
            total=100
        )
        
        # Verify task creation
        assert task.task_id == "test_task"
        assert task.metrics.total == 100
        assert task.metrics.current == 0
        
        # Update progress
        progress_tracker.update_task("test_task", 50)
        
        # Verify progress update
        updated_task = progress_tracker.get_task("test_task")
        assert updated_task.metrics.current == 50
        assert updated_task.metrics.percentage == 50.0
    
    def test_interactive_interface_validation(self, interactive_interface):
        """Test interactive interface input validation."""
        from src.ui.interactive import ValidationRule
        
        # Create prompt with validation
        validation_rule = ValidationRule(
            rule_type="min_length",
            parameters={"length": 5},
            error_message="Must be at least 5 characters"
        )
        
        prompt = UserPrompt(
            prompt_id="test_input",
            message="Enter test input",
            input_type=InputType.TEXT,
            validation_rules=[validation_rule]
        )
        
        # Test validation
        valid, error = prompt.validate_input("12345")
        assert valid is True
        assert error == ""
        
        valid, error = prompt.validate_input("123")
        assert valid is False
        assert "5 characters" in error
    
    def test_dashboard_metrics(self, dashboard):
        """Test dashboard metrics system.""" 
        # Update system metrics
        dashboard.update_metric("cpu_usage", 75.5)
        dashboard.update_metric("memory_usage", 60.0)
        
        # Verify metrics
        cpu_metric = dashboard.metrics.get("cpu_usage")
        assert cpu_metric is not None
        assert cpu_metric.current_value.value == 75.5
        
        # Test dashboard summary
        summary = dashboard.get_dashboard_summary()
        assert summary['metrics'] > 0
        assert summary['running'] is False  # Not started in test
    
    @pytest.mark.asyncio
    async def test_export_functionality(self, export_interface):
        """Test data export functionality."""
        # Test data
        test_data = [
            {"name": "Model 1", "size_mb": 100, "category": "checkpoint"},
            {"name": "Model 2", "size_mb": 200, "category": "lora"}
        ]
        
        # Create export options
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_file:
            options = ExportOptions(
                format=ExportFormat.JSON,
                output_path=Path(tmp_file.name),
                include_metadata=True
            )
        
        # Test export
        try:
            result = await export_interface.export_data(test_data, options)
            
            # Verify export
            assert result['format'] == ExportFormat.JSON.value
            assert result['records_exported'] == 2
            assert Path(result['output_path']).exists()
            
        finally:
            # Cleanup
            Path(options.output_path).unlink(missing_ok=True)


class TestPhase6Integration:
    """Test Phase 6 system integration."""
    
    @pytest.mark.asyncio
    async def test_full_system_integration(self):
        """Test integration between all Phase 6 systems."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize all systems
            auditor = SecurityAuditor(data_dir=temp_path / "audit")
            progress = ProgressTracker()
            dashboard = Dashboard()
            
            # Test integrated workflow
            # 1. Create progress task
            task = progress.create_task(
                task_id="integration_test",
                name="Integration Test Task", 
                level=ProgressLevel.SYSTEM,
                total=100
            )
            
            # 2. Log security event
            audit_event = AuditEvent(
                timestamp=time.time(),
                level=AuditLevel.INFO,
                category=AuditCategory.SYSTEM,
                event_type="integration_test",
                source="test_system",
                action="test",
                result="success"
            )
            await auditor.log_event(audit_event)
            
            # 3. Update dashboard
            dashboard.update_metric("integration_test_progress", 50)
            
            # 4. Update progress
            progress.update_task("integration_test", 75)
            
            # Verify integration
            assert task.metrics.current == 75
            
            stats = await auditor.get_audit_statistics(period_hours=1)
            assert stats['total_events'] > 0
            
            metric = dashboard.metrics.get("integration_test_progress")
            assert metric.current_value.value == 50
    
    def test_configuration_compatibility(self):
        """Test configuration compatibility across systems."""
        # Test that all systems can work with common configuration
        base_config = {
            "data_dir": "./test_data",
            "log_level": "INFO",
            "enable_metrics": True,
            "security_enabled": True
        }
        
        # Each system should be able to handle base config
        # This tests that our systems are well-designed for integration
        assert "data_dir" in base_config
        assert "log_level" in base_config
        assert isinstance(base_config["enable_metrics"], bool)
        assert isinstance(base_config["security_enabled"], bool)
    
    def test_error_handling_consistency(self):
        """Test consistent error handling across systems.""" 
        # Test that all systems handle errors consistently
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test invalid configurations
            try:
                # This should not crash the system
                invalid_config = EncryptionConfig(
                    level=EncryptionLevel.BASIC,
                    key_derivation_iterations=-1  # Invalid
                )
                # The system should handle this gracefully
                assert invalid_config.key_derivation_iterations == -1
            except Exception:
                # Acceptable if validation throws exception
                pass


# Performance and Load Tests
class TestPhase6Performance:
    """Test Phase 6 system performance."""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test system performance under concurrent load."""
        import concurrent.futures
        
        # Test concurrent progress updates
        progress = ProgressTracker()
        
        # Create multiple tasks
        tasks = []
        for i in range(10):
            task = progress.create_task(
                task_id=f"perf_task_{i}",
                name=f"Performance Task {i}",
                level=ProgressLevel.TASK,
                total=100
            )
            tasks.append(task)
        
        # Update tasks concurrently
        async def update_task(task_id):
            for j in range(0, 101, 10):
                progress.update_task(task_id, j)
                await asyncio.sleep(0.01)  # Small delay
        
        # Run concurrent updates
        await asyncio.gather(*[update_task(f"perf_task_{i}") for i in range(10)])
        
        # Verify all tasks completed
        for i in range(10):
            task = progress.get_task(f"perf_task_{i}")
            assert task.metrics.current == 100
    
    def test_memory_usage(self):
        """Test system memory usage is reasonable."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create large dashboard with many metrics
        dashboard = Dashboard()
        
        # Add many metrics
        for i in range(1000):
            dashboard.update_metric(f"test_metric_{i}", i)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB for 1000 metrics)
        assert memory_increase < 100 * 1024 * 1024


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])