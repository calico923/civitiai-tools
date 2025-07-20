#!/usr/bin/env python3
"""
Performance Optimizer for CivitAI Downloader.
Provides advanced optimization techniques for improved download performance.
"""

import asyncio
import aiohttp
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
import psutil
import threading
from collections import deque
import statistics

try:
    from ...core.config.system_config import SystemConfig
    from ...core.download.manager import DownloadManager, DownloadTask
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.config.system_config import SystemConfig
    from core.download.manager import DownloadManager, DownloadTask


class OptimizationMode(Enum):
    """Performance optimization modes."""
    SPEED = "speed"           # Maximize download speed
    EFFICIENCY = "efficiency"  # Balance speed and resource usage
    MINIMAL = "minimal"       # Minimize resource usage
    ADAPTIVE = "adaptive"     # Automatically adjust based on conditions


class NetworkCondition(Enum):
    """Network condition classifications."""
    EXCELLENT = "excellent"   # >10 MB/s
    GOOD = "good"            # 5-10 MB/s
    FAIR = "fair"            # 1-5 MB/s
    POOR = "poor"            # <1 MB/s
    UNSTABLE = "unstable"    # High variation


@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization."""
    download_speed: float = 0.0           # Current download speed (bytes/sec)
    avg_download_speed: float = 0.0       # Average download speed
    peak_download_speed: float = 0.0      # Peak download speed
    cpu_usage: float = 0.0                # Current CPU usage (%)
    memory_usage: float = 0.0             # Current memory usage (%)
    active_connections: int = 0           # Number of active connections
    failed_connections: int = 0           # Number of failed connections
    retry_count: int = 0                  # Total retry count
    network_condition: NetworkCondition = NetworkCondition.FAIR
    timestamp: float = field(default_factory=time.time)


@dataclass
class OptimizationConfig:
    """Configuration for performance optimization."""
    mode: OptimizationMode = OptimizationMode.ADAPTIVE
    max_connections: int = 10             # Maximum concurrent connections
    min_connections: int = 1              # Minimum concurrent connections
    chunk_size: int = 8192               # Download chunk size (bytes)
    max_chunk_size: int = 1048576        # Maximum chunk size (1MB)
    min_chunk_size: int = 4096           # Minimum chunk size (4KB)
    speed_sample_interval: float = 1.0    # Speed sampling interval (seconds)
    adjustment_interval: float = 5.0      # Parameter adjustment interval
    cpu_threshold: float = 80.0           # CPU usage threshold (%)
    memory_threshold: float = 80.0        # Memory usage threshold (%)
    enable_compression: bool = True       # Enable compression support
    enable_connection_pooling: bool = True # Enable connection pooling
    enable_adaptive_retry: bool = True    # Enable adaptive retry strategy


class PerformanceOptimizer:
    """Advanced performance optimization for downloads."""
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize performance optimizer.
        
        Args:
            config: System configuration
        """
        self.config = config or SystemConfig()
        
        # Optimization configuration
        self.opt_config = OptimizationConfig(
            mode=OptimizationMode(self.config.get('performance.mode', 'adaptive')),
            max_connections=self.config.get('performance.max_connections', 10),
            min_connections=self.config.get('performance.min_connections', 1),
            chunk_size=self.config.get('performance.chunk_size', 8192),
            max_chunk_size=self.config.get('performance.max_chunk_size', 1048576),
            min_chunk_size=self.config.get('performance.min_chunk_size', 4096),
            speed_sample_interval=self.config.get('performance.speed_sample_interval', 1.0),
            adjustment_interval=self.config.get('performance.adjustment_interval', 5.0),
            cpu_threshold=self.config.get('performance.cpu_threshold', 80.0),
            memory_threshold=self.config.get('performance.memory_threshold', 80.0),
            enable_compression=self.config.get('performance.enable_compression', True),
            enable_connection_pooling=self.config.get('performance.enable_connection_pooling', True),
            enable_adaptive_retry=self.config.get('performance.enable_adaptive_retry', True)
        )
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self.speed_history: deque = deque(maxlen=60)  # Last 60 speed samples
        self.cpu_history: deque = deque(maxlen=60)    # Last 60 CPU samples
        self.memory_history: deque = deque(maxlen=60) # Last 60 memory samples
        
        # Connection management
        self.active_connections: Set[str] = set()
        self.connection_speeds: Dict[str, float] = {}
        self.connection_errors: Dict[str, int] = {}
        
        # Optimization state
        self.current_connections = self.opt_config.min_connections
        self.current_chunk_size = self.opt_config.chunk_size
        self.last_adjustment_time = time.time()
        
        # Monitoring
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.Lock()
        
        # Connection pool
        self._connector = None
        self._session = None
    
    def start_monitoring(self):
        """Start performance monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Monitoring loop for system metrics."""
        while self._monitoring:
            try:
                # Update system metrics
                self.metrics.cpu_usage = psutil.cpu_percent(interval=0.1)
                self.metrics.memory_usage = psutil.virtual_memory().percent
                
                # Add to history
                self.cpu_history.append(self.metrics.cpu_usage)
                self.memory_history.append(self.metrics.memory_usage)
                
                # Check for optimization adjustments
                if self.opt_config.mode == OptimizationMode.ADAPTIVE:
                    current_time = time.time()
                    if current_time - self.last_adjustment_time >= self.opt_config.adjustment_interval:
                        self._adjust_parameters()
                        self.last_adjustment_time = current_time
                
                time.sleep(self.opt_config.speed_sample_interval)
                
            except Exception as e:
                print(f"Monitor error: {e}")
    
    def update_download_speed(self, bytes_downloaded: int, time_elapsed: float):
        """
        Update download speed metrics.
        
        Args:
            bytes_downloaded: Bytes downloaded in the interval
            time_elapsed: Time elapsed (seconds)
        """
        if time_elapsed <= 0:
            return
        
        speed = bytes_downloaded / time_elapsed
        
        with self._lock:
            self.speed_history.append(speed)
            self.metrics.download_speed = speed
            
            # Update average speed
            if self.speed_history:
                self.metrics.avg_download_speed = statistics.mean(self.speed_history)
                self.metrics.peak_download_speed = max(self.metrics.peak_download_speed, speed)
            
            # Classify network condition
            self._classify_network_condition()
    
    def _classify_network_condition(self):
        """Classify current network condition based on speed history."""
        if len(self.speed_history) < 5:
            return
        
        avg_speed = statistics.mean(self.speed_history)
        std_dev = statistics.stdev(self.speed_history) if len(self.speed_history) > 1 else 0
        
        # Speed-based classification (bytes/sec)
        if avg_speed > 10 * 1024 * 1024:  # >10 MB/s
            base_condition = NetworkCondition.EXCELLENT
        elif avg_speed > 5 * 1024 * 1024:  # >5 MB/s
            base_condition = NetworkCondition.GOOD
        elif avg_speed > 1024 * 1024:      # >1 MB/s
            base_condition = NetworkCondition.FAIR
        else:
            base_condition = NetworkCondition.POOR
        
        # Check stability
        if std_dev > avg_speed * 0.5:  # High variation
            self.metrics.network_condition = NetworkCondition.UNSTABLE
        else:
            self.metrics.network_condition = base_condition
    
    def _adjust_parameters(self):
        """Adjust optimization parameters based on current conditions."""
        # Adjust concurrent connections
        if self.metrics.cpu_usage < 50 and self.metrics.memory_usage < 50:
            # System has resources, increase connections
            if self.metrics.network_condition in [NetworkCondition.EXCELLENT, NetworkCondition.GOOD]:
                self.current_connections = min(
                    self.current_connections + 1,
                    self.opt_config.max_connections
                )
        elif self.metrics.cpu_usage > self.opt_config.cpu_threshold or \
             self.metrics.memory_usage > self.opt_config.memory_threshold:
            # System under stress, reduce connections
            self.current_connections = max(
                self.current_connections - 1,
                self.opt_config.min_connections
            )
        
        # Adjust chunk size based on network condition
        if self.metrics.network_condition == NetworkCondition.EXCELLENT:
            # Increase chunk size for better throughput
            self.current_chunk_size = min(
                self.current_chunk_size * 2,
                self.opt_config.max_chunk_size
            )
        elif self.metrics.network_condition in [NetworkCondition.POOR, NetworkCondition.UNSTABLE]:
            # Decrease chunk size for better reliability
            self.current_chunk_size = max(
                self.current_chunk_size // 2,
                self.opt_config.min_chunk_size
            )
    
    def get_optimal_connections(self) -> int:
        """
        Get optimal number of concurrent connections.
        
        Returns:
            Optimal connection count
        """
        if self.opt_config.mode == OptimizationMode.SPEED:
            return self.opt_config.max_connections
        elif self.opt_config.mode == OptimizationMode.MINIMAL:
            return self.opt_config.min_connections
        elif self.opt_config.mode == OptimizationMode.EFFICIENCY:
            # Balance between speed and resources
            return max(self.opt_config.min_connections, self.opt_config.max_connections // 2)
        else:  # ADAPTIVE
            return self.current_connections
    
    def get_optimal_chunk_size(self) -> int:
        """
        Get optimal chunk size for downloads.
        
        Returns:
            Optimal chunk size in bytes
        """
        if self.opt_config.mode == OptimizationMode.SPEED:
            return self.opt_config.max_chunk_size
        elif self.opt_config.mode == OptimizationMode.MINIMAL:
            return self.opt_config.min_chunk_size
        elif self.opt_config.mode == OptimizationMode.EFFICIENCY:
            return self.opt_config.chunk_size
        else:  # ADAPTIVE
            return self.current_chunk_size
    
    def get_retry_delay(self, attempt: int) -> float:
        """
        Get optimized retry delay based on conditions.
        
        Args:
            attempt: Retry attempt number
            
        Returns:
            Delay in seconds
        """
        if not self.opt_config.enable_adaptive_retry:
            # Standard exponential backoff
            return min(2 ** attempt, 60)
        
        # Adaptive retry based on network condition
        base_delay = 1.0
        
        if self.metrics.network_condition == NetworkCondition.EXCELLENT:
            base_delay = 0.5
        elif self.metrics.network_condition == NetworkCondition.POOR:
            base_delay = 2.0
        elif self.metrics.network_condition == NetworkCondition.UNSTABLE:
            base_delay = 3.0
        
        # Apply exponential backoff with jitter
        delay = base_delay * (2 ** attempt)
        jitter = delay * 0.1 * (0.5 - threading.current_thread().ident % 100 / 100)
        
        return min(delay + jitter, 60)
    
    async def create_optimized_session(self) -> aiohttp.ClientSession:
        """
        Create an optimized aiohttp session.
        
        Returns:
            Optimized client session
        """
        if self._session and not self._session.closed:
            return self._session
        
        # Create optimized connector
        connector_kwargs = {
            'limit': self.get_optimal_connections(),
            'limit_per_host': self.get_optimal_connections(),
            'ttl_dns_cache': 300,  # DNS cache for 5 minutes
            'enable_cleanup_closed': True
        }
        
        if self.opt_config.enable_connection_pooling:
            connector_kwargs['keepalive_timeout'] = 30
            connector_kwargs['force_close'] = False
        
        self._connector = aiohttp.TCPConnector(**connector_kwargs)
        
        # Create session with optimized settings
        timeout = aiohttp.ClientTimeout(
            total=None,
            connect=30,
            sock_connect=30,
            sock_read=30
        )
        
        headers = {}
        if self.opt_config.enable_compression:
            headers['Accept-Encoding'] = 'gzip, deflate, br'
        
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers=headers
        )
        
        return self._session
    
    async def close_session(self):
        """Close the optimized session."""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector:
            await self._connector.close()
    
    def register_connection(self, connection_id: str):
        """Register an active connection."""
        with self._lock:
            self.active_connections.add(connection_id)
            self.metrics.active_connections = len(self.active_connections)
    
    def unregister_connection(self, connection_id: str):
        """Unregister a connection."""
        with self._lock:
            self.active_connections.discard(connection_id)
            self.metrics.active_connections = len(self.active_connections)
    
    def record_connection_error(self, connection_id: str):
        """Record a connection error."""
        with self._lock:
            self.connection_errors[connection_id] = self.connection_errors.get(connection_id, 0) + 1
            self.metrics.failed_connections = sum(self.connection_errors.values())
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.
        
        Returns:
            Performance metrics and recommendations
        """
        report = {
            'metrics': {
                'current_speed': self.metrics.download_speed,
                'average_speed': self.metrics.avg_download_speed,
                'peak_speed': self.metrics.peak_download_speed,
                'network_condition': self.metrics.network_condition.value,
                'cpu_usage': self.metrics.cpu_usage,
                'memory_usage': self.metrics.memory_usage,
                'active_connections': self.metrics.active_connections,
                'failed_connections': self.metrics.failed_connections,
                'retry_count': self.metrics.retry_count
            },
            'configuration': {
                'mode': self.opt_config.mode.value,
                'current_connections': self.current_connections,
                'current_chunk_size': self.current_chunk_size,
                'compression_enabled': self.opt_config.enable_compression,
                'connection_pooling': self.opt_config.enable_connection_pooling,
                'adaptive_retry': self.opt_config.enable_adaptive_retry
            },
            'recommendations': self._get_recommendations()
        }
        
        return report
    
    def _get_recommendations(self) -> List[str]:
        """Get performance recommendations based on current metrics."""
        recommendations = []
        
        # Network recommendations
        if self.metrics.network_condition == NetworkCondition.POOR:
            recommendations.append("Network speed is poor. Consider reducing concurrent downloads.")
        elif self.metrics.network_condition == NetworkCondition.UNSTABLE:
            recommendations.append("Network is unstable. Enable adaptive retry for better reliability.")
        
        # Resource recommendations
        if self.metrics.cpu_usage > self.opt_config.cpu_threshold:
            recommendations.append(f"CPU usage is high ({self.metrics.cpu_usage:.1f}%). Reduce concurrent operations.")
        
        if self.metrics.memory_usage > self.opt_config.memory_threshold:
            recommendations.append(f"Memory usage is high ({self.metrics.memory_usage:.1f}%). Reduce chunk size.")
        
        # Connection recommendations
        failure_rate = self.metrics.failed_connections / max(self.metrics.active_connections, 1)
        if failure_rate > 0.1:
            recommendations.append("High connection failure rate. Check network stability and server availability.")
        
        # Performance recommendations
        if self.metrics.avg_download_speed < 1024 * 1024:  # <1 MB/s
            recommendations.append("Average download speed is low. Check network connection and server location.")
        
        return recommendations


class AdaptiveDownloadManager(DownloadManager):
    """Download manager with performance optimization."""
    
    def __init__(self, optimizer: Optional[PerformanceOptimizer] = None, 
                 config: Optional[SystemConfig] = None):
        """
        Initialize adaptive download manager.
        
        Args:
            optimizer: Performance optimizer instance
            config: System configuration
        """
        super().__init__(config)
        self.optimizer = optimizer or PerformanceOptimizer(config)
        self.optimizer.start_monitoring()
        
        # Override configuration with optimized values
        self._update_configuration()
    
    def _update_configuration(self):
        """Update configuration based on optimizer."""
        self.concurrent_downloads = self.optimizer.get_optimal_connections()
        self.chunk_size = self.optimizer.get_optimal_chunk_size()
    
    async def _download_file(self, task: DownloadTask) -> None:
        """Enhanced download with performance tracking."""
        connection_id = f"conn_{task.id}"
        self.optimizer.register_connection(connection_id)
        
        try:
            # Periodically update configuration
            self._update_configuration()
            
            # Track download speed
            start_time = time.time()
            start_bytes = task.downloaded_bytes
            
            # Call parent download method
            await super()._download_file(task)
            
            # Update metrics
            elapsed = time.time() - start_time
            bytes_downloaded = task.downloaded_bytes - start_bytes
            if elapsed > 0:
                self.optimizer.update_download_speed(bytes_downloaded, elapsed)
                
        except Exception as e:
            self.optimizer.record_connection_error(connection_id)
            raise
            
        finally:
            self.optimizer.unregister_connection(connection_id)
    
    async def close(self):
        """Close download manager and optimizer."""
        await super().close()
        await self.optimizer.close_session()
        self.optimizer.stop_monitoring()


# Utility functions
def create_optimized_download_manager(mode: str = "adaptive") -> AdaptiveDownloadManager:
    """
    Create a download manager with performance optimization.
    
    Args:
        mode: Optimization mode (speed, efficiency, minimal, adaptive)
        
    Returns:
        Optimized download manager
    """
    config = SystemConfig()
    config.set('performance.mode', mode)
    
    optimizer = PerformanceOptimizer(config)
    return AdaptiveDownloadManager(optimizer, config)


def benchmark_download_performance(url: str, 
                                 sizes: List[int] = None,
                                 connections: List[int] = None) -> Dict[str, Any]:
    """
    Benchmark download performance with different configurations.
    
    Args:
        url: URL to test
        sizes: Chunk sizes to test
        connections: Connection counts to test
        
    Returns:
        Benchmark results
    """
    # Implementation would perform actual benchmarking
    # This is a placeholder for the concept
    raise NotImplementedError("Benchmark functionality requires actual download testing")


if __name__ == "__main__":
    # Test performance optimizer
    print("Testing Performance Optimizer...")
    
    optimizer = PerformanceOptimizer()
    optimizer.start_monitoring()
    
    # Simulate some metrics
    optimizer.update_download_speed(1024 * 1024 * 5, 1.0)  # 5 MB/s
    time.sleep(1)
    
    # Get performance report
    report = optimizer.get_performance_report()
    print(f"Performance Report:")
    print(f"  Network Condition: {report['metrics']['network_condition']}")
    print(f"  CPU Usage: {report['metrics']['cpu_usage']:.1f}%")
    print(f"  Memory Usage: {report['metrics']['memory_usage']:.1f}%")
    print(f"  Optimal Connections: {report['configuration']['current_connections']}")
    print(f"  Optimal Chunk Size: {report['configuration']['current_chunk_size']} bytes")
    
    if report['recommendations']:
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    optimizer.stop_monitoring()
    print("\nPerformance Optimizer test completed.")