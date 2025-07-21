#!/usr/bin/env python3
"""
Tests for Performance Optimizer.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import statistics
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.performance.optimizer import (
    PerformanceOptimizer, AdaptiveDownloadManager,
    OptimizationMode, NetworkCondition, PerformanceMetrics,
    OptimizationConfig, create_optimized_download_manager
)


class TestPerformanceMetrics:
    """Test PerformanceMetrics data class."""
    
    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics creation with defaults."""
        metrics = PerformanceMetrics()
        
        assert metrics.download_speed == 0.0
        assert metrics.avg_download_speed == 0.0
        assert metrics.peak_download_speed == 0.0
        assert metrics.cpu_usage == 0.0
        assert metrics.memory_usage == 0.0
        assert metrics.active_connections == 0
        assert metrics.failed_connections == 0
        assert metrics.retry_count == 0
        assert metrics.network_condition == NetworkCondition.FAIR
        assert isinstance(metrics.timestamp, float)
    
    def test_performance_metrics_custom_values(self):
        """Test PerformanceMetrics with custom values."""
        metrics = PerformanceMetrics(
            download_speed=1024 * 1024,  # 1 MB/s
            cpu_usage=45.5,
            memory_usage=60.0,
            active_connections=5,
            network_condition=NetworkCondition.EXCELLENT
        )
        
        assert metrics.download_speed == 1024 * 1024
        assert metrics.cpu_usage == 45.5
        assert metrics.memory_usage == 60.0
        assert metrics.active_connections == 5
        assert metrics.network_condition == NetworkCondition.EXCELLENT


class TestOptimizationConfig:
    """Test OptimizationConfig data class."""
    
    def test_optimization_config_defaults(self):
        """Test OptimizationConfig default values."""
        config = OptimizationConfig()
        
        assert config.mode == OptimizationMode.ADAPTIVE
        assert config.max_connections == 10
        assert config.min_connections == 1
        assert config.chunk_size == 8192
        assert config.max_chunk_size == 1048576
        assert config.min_chunk_size == 4096
        assert config.speed_sample_interval == 1.0
        assert config.adjustment_interval == 5.0
        assert config.cpu_threshold == 80.0
        assert config.memory_threshold == 80.0
        assert config.enable_compression is True
        assert config.enable_connection_pooling is True
        assert config.enable_adaptive_retry is True
    
    def test_optimization_config_custom_values(self):
        """Test OptimizationConfig with custom values."""
        config = OptimizationConfig(
            mode=OptimizationMode.SPEED,
            max_connections=20,
            chunk_size=16384,
            enable_compression=False
        )
        
        assert config.mode == OptimizationMode.SPEED
        assert config.max_connections == 20
        assert config.chunk_size == 16384
        assert config.enable_compression is False


class TestPerformanceOptimizer:
    """Test PerformanceOptimizer functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock configuration
        self.mock_config = Mock()
        self.mock_config.get.side_effect = lambda key, default=None: {
            'performance.mode': 'adaptive',
            'performance.max_connections': 8,
            'performance.min_connections': 2,
            'performance.chunk_size': 16384,
            'performance.cpu_threshold': 75.0,
            'performance.memory_threshold': 75.0
        }.get(key, default)
        
        # Create optimizer
        self.optimizer = PerformanceOptimizer(self.mock_config)
    
    def test_initialization(self):
        """Test PerformanceOptimizer initialization."""
        assert self.optimizer.opt_config.mode == OptimizationMode.ADAPTIVE
        assert self.optimizer.opt_config.max_connections == 8
        assert self.optimizer.opt_config.min_connections == 2
        assert self.optimizer.opt_config.chunk_size == 16384
        assert self.optimizer.opt_config.cpu_threshold == 75.0
        assert self.optimizer.opt_config.memory_threshold == 75.0
        assert self.optimizer.current_connections == 2  # Starts at minimum
        assert self.optimizer.current_chunk_size == 16384
    
    def test_update_download_speed(self):
        """Test updating download speed metrics."""
        # Update speed multiple times
        self.optimizer.update_download_speed(1024 * 1024, 1.0)  # 1 MB/s
        self.optimizer.update_download_speed(2 * 1024 * 1024, 1.0)  # 2 MB/s
        self.optimizer.update_download_speed(1.5 * 1024 * 1024, 1.0)  # 1.5 MB/s
        
        assert self.optimizer.metrics.download_speed == 1.5 * 1024 * 1024
        assert len(self.optimizer.speed_history) == 3
        assert self.optimizer.metrics.avg_download_speed == pytest.approx(1.5 * 1024 * 1024, rel=0.1)
        assert self.optimizer.metrics.peak_download_speed == 2 * 1024 * 1024
    
    def test_network_condition_classification(self):
        """Test network condition classification."""
        # Test EXCELLENT condition (>10 MB/s)
        for _ in range(10):
            self.optimizer.update_download_speed(12 * 1024 * 1024, 1.0)
        assert self.optimizer.metrics.network_condition == NetworkCondition.EXCELLENT
        
        # Reset and test GOOD condition (5-10 MB/s)
        self.optimizer.speed_history.clear()
        for _ in range(10):
            self.optimizer.update_download_speed(7 * 1024 * 1024, 1.0)
        assert self.optimizer.metrics.network_condition == NetworkCondition.GOOD
        
        # Reset and test FAIR condition (1-5 MB/s)
        self.optimizer.speed_history.clear()
        for _ in range(10):
            self.optimizer.update_download_speed(2 * 1024 * 1024, 1.0)
        assert self.optimizer.metrics.network_condition == NetworkCondition.FAIR
        
        # Reset and test POOR condition (<1 MB/s)
        self.optimizer.speed_history.clear()
        for _ in range(10):
            self.optimizer.update_download_speed(512 * 1024, 1.0)
        assert self.optimizer.metrics.network_condition == NetworkCondition.POOR
    
    def test_network_stability_detection(self):
        """Test unstable network detection."""
        # Add highly variable speeds
        speeds = [1024 * 1024, 10 * 1024 * 1024, 512 * 1024, 8 * 1024 * 1024, 256 * 1024]
        for speed in speeds:
            self.optimizer.update_download_speed(speed, 1.0)
        
        # Should detect as unstable due to high variation
        assert self.optimizer.metrics.network_condition == NetworkCondition.UNSTABLE
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_parameter_adjustment_increase_connections(self, mock_memory, mock_cpu):
        """Test parameter adjustment when resources are available."""
        # Mock low resource usage
        mock_cpu.return_value = 30.0
        mock_memory.return_value = Mock(percent=40.0)
        
        # Set good network condition
        for _ in range(10):
            self.optimizer.update_download_speed(8 * 1024 * 1024, 1.0)
        
        # Update metrics
        self.optimizer.metrics.cpu_usage = 30.0
        self.optimizer.metrics.memory_usage = 40.0
        
        # Adjust parameters
        initial_connections = self.optimizer.current_connections
        self.optimizer._adjust_parameters()
        
        # Should increase connections
        assert self.optimizer.current_connections > initial_connections
        assert self.optimizer.current_connections <= self.optimizer.opt_config.max_connections
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_parameter_adjustment_decrease_connections(self, mock_memory, mock_cpu):
        """Test parameter adjustment when resources are limited."""
        # Mock high resource usage
        mock_cpu.return_value = 85.0
        mock_memory.return_value = Mock(percent=80.0)
        
        # Start with more connections
        self.optimizer.current_connections = 5
        
        # Update metrics
        self.optimizer.metrics.cpu_usage = 85.0
        self.optimizer.metrics.memory_usage = 80.0
        
        # Adjust parameters
        initial_connections = self.optimizer.current_connections
        self.optimizer._adjust_parameters()
        
        # Should decrease connections
        assert self.optimizer.current_connections < initial_connections
        assert self.optimizer.current_connections >= self.optimizer.opt_config.min_connections
    
    def test_chunk_size_adjustment(self):
        """Test chunk size adjustment based on network condition."""
        # Test increase for excellent network
        initial_chunk_size = self.optimizer.current_chunk_size
        for _ in range(10):
            self.optimizer.update_download_speed(15 * 1024 * 1024, 1.0)
        self.optimizer._adjust_parameters()
        assert self.optimizer.current_chunk_size > initial_chunk_size
        
        # Test decrease for poor network
        self.optimizer.speed_history.clear()
        for _ in range(10):
            self.optimizer.update_download_speed(256 * 1024, 1.0)
        initial_chunk_size = self.optimizer.current_chunk_size
        self.optimizer._adjust_parameters()
        assert self.optimizer.current_chunk_size < initial_chunk_size
    
    def test_get_optimal_connections_by_mode(self):
        """Test getting optimal connections for different modes."""
        # SPEED mode
        self.optimizer.opt_config.mode = OptimizationMode.SPEED
        assert self.optimizer.get_optimal_connections() == self.optimizer.opt_config.max_connections
        
        # MINIMAL mode
        self.optimizer.opt_config.mode = OptimizationMode.MINIMAL
        assert self.optimizer.get_optimal_connections() == self.optimizer.opt_config.min_connections
        
        # EFFICIENCY mode
        self.optimizer.opt_config.mode = OptimizationMode.EFFICIENCY
        expected = max(self.optimizer.opt_config.min_connections, 
                      self.optimizer.opt_config.max_connections // 2)
        assert self.optimizer.get_optimal_connections() == expected
        
        # ADAPTIVE mode
        self.optimizer.opt_config.mode = OptimizationMode.ADAPTIVE
        self.optimizer.current_connections = 5
        assert self.optimizer.get_optimal_connections() == 5
    
    def test_get_optimal_chunk_size_by_mode(self):
        """Test getting optimal chunk size for different modes."""
        # SPEED mode
        self.optimizer.opt_config.mode = OptimizationMode.SPEED
        assert self.optimizer.get_optimal_chunk_size() == self.optimizer.opt_config.max_chunk_size
        
        # MINIMAL mode
        self.optimizer.opt_config.mode = OptimizationMode.MINIMAL
        assert self.optimizer.get_optimal_chunk_size() == self.optimizer.opt_config.min_chunk_size
        
        # EFFICIENCY mode
        self.optimizer.opt_config.mode = OptimizationMode.EFFICIENCY
        assert self.optimizer.get_optimal_chunk_size() == self.optimizer.opt_config.chunk_size
        
        # ADAPTIVE mode
        self.optimizer.opt_config.mode = OptimizationMode.ADAPTIVE
        self.optimizer.current_chunk_size = 32768
        assert self.optimizer.get_optimal_chunk_size() == 32768
    
    def test_retry_delay_standard(self):
        """Test standard retry delay calculation."""
        self.optimizer.opt_config.enable_adaptive_retry = False
        
        # Test exponential backoff
        assert self.optimizer.get_retry_delay(0) == 1.0
        assert self.optimizer.get_retry_delay(1) == 2.0
        assert self.optimizer.get_retry_delay(2) == 4.0
        assert self.optimizer.get_retry_delay(3) == 8.0
        assert self.optimizer.get_retry_delay(10) == 60.0  # Max cap
    
    def test_retry_delay_adaptive(self):
        """Test adaptive retry delay calculation."""
        self.optimizer.opt_config.enable_adaptive_retry = True
        
        # Test with excellent network
        self.optimizer.metrics.network_condition = NetworkCondition.EXCELLENT
        delay = self.optimizer.get_retry_delay(1)
        assert delay >= 1.0  # Base 0.5 * 2^1
        assert delay <= 1.2  # With jitter
        
        # Test with poor network
        self.optimizer.metrics.network_condition = NetworkCondition.POOR
        delay = self.optimizer.get_retry_delay(1)
        assert delay >= 3.8  # Base 2.0 * 2^1
        assert delay <= 4.2  # With jitter
    
    @pytest.mark.asyncio
    async def test_create_optimized_session(self):
        """Test creating optimized aiohttp session."""
        self.optimizer.current_connections = 5
        
        session = await self.optimizer.create_optimized_session()
        
        assert session is not None
        assert not session.closed
        assert self.optimizer._connector is not None
        assert self.optimizer._connector._limit == 5
        
        # Test compression headers when enabled
        assert 'Accept-Encoding' in session.headers
        
        await self.optimizer.close_session()
    
    def test_connection_tracking(self):
        """Test connection registration and tracking."""
        # Register connections
        self.optimizer.register_connection("conn1")
        self.optimizer.register_connection("conn2")
        
        assert self.optimizer.metrics.active_connections == 2
        assert "conn1" in self.optimizer.active_connections
        assert "conn2" in self.optimizer.active_connections
        
        # Unregister connection
        self.optimizer.unregister_connection("conn1")
        
        assert self.optimizer.metrics.active_connections == 1
        assert "conn1" not in self.optimizer.active_connections
        
        # Record errors
        self.optimizer.record_connection_error("conn2")
        self.optimizer.record_connection_error("conn2")
        
        assert self.optimizer.metrics.failed_connections == 2
        assert self.optimizer.connection_errors["conn2"] == 2
    
    def test_performance_report(self):
        """Test performance report generation."""
        # Set up some metrics
        self.optimizer.update_download_speed(5 * 1024 * 1024, 1.0)
        self.optimizer.metrics.cpu_usage = 45.0
        self.optimizer.metrics.memory_usage = 60.0
        self.optimizer.metrics.active_connections = 3
        self.optimizer.metrics.failed_connections = 1
        
        report = self.optimizer.get_performance_report()
        
        assert 'metrics' in report
        assert 'configuration' in report
        assert 'recommendations' in report
        
        # Check metrics
        assert report['metrics']['current_speed'] == 5 * 1024 * 1024
        assert report['metrics']['cpu_usage'] == 45.0
        assert report['metrics']['memory_usage'] == 60.0
        assert report['metrics']['active_connections'] == 3
        
        # Check configuration
        assert report['configuration']['mode'] == 'adaptive'
        assert report['configuration']['compression_enabled'] is True
    
    def test_recommendations(self):
        """Test performance recommendations."""
        # Test poor network recommendation
        self.optimizer.metrics.network_condition = NetworkCondition.POOR
        report = self.optimizer.get_performance_report()
        assert any("Network speed is poor" in rec for rec in report['recommendations'])
        
        # Test high CPU recommendation
        self.optimizer.metrics.cpu_usage = 85.0
        report = self.optimizer.get_performance_report()
        assert any("CPU usage is high" in rec for rec in report['recommendations'])
        
        # Test high failure rate recommendation
        self.optimizer.metrics.active_connections = 10
        self.optimizer.metrics.failed_connections = 3
        report = self.optimizer.get_performance_report()
        assert any("High connection failure rate" in rec for rec in report['recommendations'])
    
    @patch('threading.Thread')
    def test_monitoring_start_stop(self, mock_thread):
        """Test monitoring thread start and stop."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        # Start monitoring
        self.optimizer.start_monitoring()
        assert self.optimizer._monitoring is True
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        
        # Stop monitoring
        self.optimizer.stop_monitoring()
        assert self.optimizer._monitoring is False
        mock_thread_instance.join.assert_called_once_with(timeout=5)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.net_io_counters')
    def test_complex_adverse_conditions_parameter_stability(self, mock_net_io, mock_memory, mock_cpu):
        """Test parameter adjustment stability under complex adverse conditions."""
        # Setup: CPU high, memory high, network unstable (triple threat scenario)
        mock_cpu.return_value = 95.0  # Very high CPU
        mock_memory.return_value = Mock(percent=88.0)  # High memory usage
        mock_net_io.return_value = Mock(
            bytes_sent=1000000,
            bytes_recv=500000,
            packets_sent=1000,
            packets_recv=800,
            errin=50,  # High error rate - network issues
            errout=30,
            dropin=20,  # Packet drops
            dropout=15
        )
        
        # Start with moderate settings
        self.optimizer.current_connections = 5
        self.optimizer.current_chunk_size = 32768
        
        # Track parameter changes over multiple adjustment cycles
        connection_history = []
        chunk_size_history = []
        
        # Simulate multiple adjustment cycles under adverse conditions
        for cycle in range(10):
            # Update metrics with adverse conditions
            self.optimizer.metrics.cpu_usage = 95.0
            self.optimizer.metrics.memory_usage = 88.0
            self.optimizer.metrics.network_condition = NetworkCondition.UNSTABLE
            
            # Add some speed variance to simulate network instability
            unstable_speed = 100 * 1024 * (1.0 + 0.5 * (cycle % 3 - 1))  # Varies between 50KB/s to 150KB/s
            self.optimizer.update_download_speed(unstable_speed, 1.0)
            
            # Perform adjustment
            self.optimizer._adjust_parameters()
            
            # Record post-adjustment values
            connection_history.append(self.optimizer.current_connections)
            chunk_size_history.append(self.optimizer.current_chunk_size)
            
            # Ensure parameters stay within bounds
            assert (self.optimizer.opt_config.min_connections <= 
                   self.optimizer.current_connections <= 
                   self.optimizer.opt_config.max_connections), \
                   f"Connections out of bounds at cycle {cycle}: {self.optimizer.current_connections}"
            
            assert (self.optimizer.opt_config.min_chunk_size <= 
                   self.optimizer.current_chunk_size <= 
                   self.optimizer.opt_config.max_chunk_size), \
                   f"Chunk size out of bounds at cycle {cycle}: {self.optimizer.current_chunk_size}"
        
        # Verify parameter stability - should converge to safe values
        final_connections = connection_history[-1]
        final_chunk_size = chunk_size_history[-1]
        
        # Under extreme adverse conditions, should converge to minimal safe values
        assert final_connections == self.optimizer.opt_config.min_connections, \
            "Should converge to minimum connections under adverse conditions"
        
        assert final_chunk_size <= self.optimizer.opt_config.min_chunk_size * 2, \
            "Should converge to small chunk size under adverse conditions"
        
        # Check for oscillation - parameters shouldn't wildly swing back and forth
        if len(connection_history) >= 5:
            recent_connections = connection_history[-5:]
            connection_variance = statistics.variance(recent_connections) if len(set(recent_connections)) > 1 else 0
            assert connection_variance <= 2.0, \
                f"Connection count shouldn't oscillate wildly: variance={connection_variance}, history={recent_connections}"
        
        # Verify the system reaches a stable state (last 3 cycles should be similar)
        if len(connection_history) >= 3:
            last_three_connections = connection_history[-3:]
            assert max(last_three_connections) - min(last_three_connections) <= 1, \
                "Should reach stable connection count in final cycles"


class TestAdaptiveDownloadManager:
    """Test AdaptiveDownloadManager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock optimizer
        self.mock_optimizer = Mock(spec=PerformanceOptimizer)
        self.mock_optimizer.get_optimal_connections.return_value = 5
        self.mock_optimizer.get_optimal_chunk_size.return_value = 16384
        self.mock_optimizer.close_session = AsyncMock()
        self.mock_optimizer.stop_monitoring = Mock()
        
        # Mock config
        self.mock_config = Mock()
        self.mock_config.get.return_value = None
    
    @patch('core.performance.optimizer.DownloadManager.__init__')
    def test_initialization(self, mock_super_init):
        """Test AdaptiveDownloadManager initialization."""
        mock_super_init.return_value = None
        
        manager = AdaptiveDownloadManager(self.mock_optimizer, self.mock_config)
        
        assert manager.optimizer == self.mock_optimizer
        self.mock_optimizer.start_monitoring.assert_called_once()
        assert manager.concurrent_downloads == 5
        assert manager.chunk_size == 16384
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing adaptive download manager."""
        with patch('core.performance.optimizer.DownloadManager.__init__', return_value=None):
            with patch('core.performance.optimizer.DownloadManager.close', new_callable=AsyncMock):
                manager = AdaptiveDownloadManager(self.mock_optimizer, self.mock_config)
                
                await manager.close()
                
                self.mock_optimizer.close_session.assert_called_once()
                self.mock_optimizer.stop_monitoring.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""
    
    @patch('core.performance.optimizer.AdaptiveDownloadManager')
    @patch('core.performance.optimizer.PerformanceOptimizer')
    @patch('core.performance.optimizer.SystemConfig')
    def test_create_optimized_download_manager(self, mock_config_class, mock_optimizer_class, mock_manager_class):
        """Test creating optimized download manager."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_optimizer = Mock()
        mock_optimizer_class.return_value = mock_optimizer
        
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        result = create_optimized_download_manager("speed")
        
        mock_config.set.assert_called_once_with('performance.mode', 'speed')
        mock_optimizer_class.assert_called_once_with(mock_config)
        mock_manager_class.assert_called_once_with(mock_optimizer, mock_config)
        assert result == mock_manager
    
    def test_benchmark_download_performance_not_implemented(self):
        """Test that benchmark function is not implemented."""
        from core.performance.optimizer import benchmark_download_performance
        
        with pytest.raises(NotImplementedError):
            benchmark_download_performance("http://example.com/file")


class TestEnums:
    """Test performance optimization enums."""
    
    def test_optimization_mode_enum(self):
        """Test OptimizationMode enum values."""
        assert OptimizationMode.SPEED.value == "speed"
        assert OptimizationMode.EFFICIENCY.value == "efficiency"
        assert OptimizationMode.MINIMAL.value == "minimal"
        assert OptimizationMode.ADAPTIVE.value == "adaptive"
    
    def test_network_condition_enum(self):
        """Test NetworkCondition enum values."""
        assert NetworkCondition.EXCELLENT.value == "excellent"
        assert NetworkCondition.GOOD.value == "good"
        assert NetworkCondition.FAIR.value == "fair"
        assert NetworkCondition.POOR.value == "poor"
        assert NetworkCondition.UNSTABLE.value == "unstable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])