#!/usr/bin/env python3
"""
Health Check System.
Implements requirement 17.2: System health monitoring and degradation detection.
"""

import logging
import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Individual health metric."""
    name: str
    value: Any
    status: HealthStatus
    threshold: Optional[float] = None
    message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class SystemHealth:
    """Overall system health information."""
    status: HealthStatus
    metrics: Dict[str, HealthMetric] = field(default_factory=dict)
    last_check: float = field(default_factory=time.time)
    uptime: float = 0.0
    
    def add_metric(self, metric: HealthMetric) -> None:
        """Add a health metric."""
        self.metrics[metric.name] = metric
        
        # Update overall status (worst status wins)
        if metric.status == HealthStatus.CRITICAL:
            self.status = HealthStatus.CRITICAL
        elif metric.status == HealthStatus.WARNING and self.status != HealthStatus.CRITICAL:
            self.status = HealthStatus.WARNING
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health summary."""
        critical_count = len([m for m in self.metrics.values() if m.status == HealthStatus.CRITICAL])
        warning_count = len([m for m in self.metrics.values() if m.status == HealthStatus.WARNING])
        healthy_count = len([m for m in self.metrics.values() if m.status == HealthStatus.HEALTHY])
        
        return {
            "overall_status": self.status.value,
            "last_check": self.last_check,
            "uptime": self.uptime,
            "metrics_summary": {
                "total": len(self.metrics),
                "critical": critical_count,
                "warning": warning_count,
                "healthy": healthy_count
            },
            "critical_issues": [
                {"name": m.name, "message": m.message}
                for m in self.metrics.values()
                if m.status == HealthStatus.CRITICAL
            ],
            "warnings": [
                {"name": m.name, "message": m.message}
                for m in self.metrics.values()
                if m.status == HealthStatus.WARNING
            ]
        }


class HealthChecker:
    """
    System health monitoring and diagnostics.
    Implements requirement 17.2: Health monitoring with thresholds.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize health checker.
        
        Args:
            data_dir: Application data directory
        """
        self.data_dir = data_dir or Path("./data")
        self.start_time = time.time()
        
        # Health thresholds
        self.thresholds = {
            "cpu_usage": {"warning": 80.0, "critical": 95.0},  # Percentage
            "memory_usage": {"warning": 85.0, "critical": 95.0},  # Percentage
            "disk_usage": {"warning": 85.0, "critical": 95.0},  # Percentage
            "api_response_time": {"warning": 5.0, "critical": 10.0},  # Seconds
            "error_rate": {"warning": 0.1, "critical": 0.25},  # Percentage (0-1)
            "db_size": {"warning": 1000, "critical": 5000}  # MB
        }
        
        # Custom health checks
        self.custom_checks: List[Callable[[], HealthMetric]] = []
        
        # Recent metrics for trend analysis
        self.metric_history: Dict[str, List[HealthMetric]] = {}
    
    async def check_system_health(self) -> SystemHealth:
        """
        Perform comprehensive system health check.
        
        Returns:
            SystemHealth object with current status
        """
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            uptime=time.time() - self.start_time
        )
        
        # Check all health metrics
        checks = [
            self._check_cpu_usage(),
            self._check_memory_usage(),
            self._check_disk_usage(),
            self._check_api_connectivity(),
            self._check_database_health(),
            self._check_file_permissions(),
            self._check_network_connectivity()
        ]
        
        # Run all checks concurrently
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                error_metric = HealthMetric(
                    name="check_error",
                    value=str(result),
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {result}"
                )
                health.add_metric(error_metric)
            elif isinstance(result, HealthMetric):
                health.add_metric(result)
                self._record_metric_history(result)
        
        # Run custom checks
        for custom_check in self.custom_checks:
            try:
                metric = custom_check()
                health.add_metric(metric)
                self._record_metric_history(metric)
            except Exception as e:
                logger.error(f"Custom health check failed: {e}")
        
        health.last_check = time.time()
        return health
    
    async def _check_cpu_usage(self) -> HealthMetric:
        """Check CPU usage."""
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)
            
            status = HealthStatus.HEALTHY
            message = f"CPU usage: {cpu_percent:.1f}%"
            
            if cpu_percent >= self.thresholds["cpu_usage"]["critical"]:
                status = HealthStatus.CRITICAL
                message = f"CRITICAL: High CPU usage at {cpu_percent:.1f}%"
            elif cpu_percent >= self.thresholds["cpu_usage"]["warning"]:
                status = HealthStatus.WARNING
                message = f"WARNING: Elevated CPU usage at {cpu_percent:.1f}%"
            
            return HealthMetric(
                name="cpu_usage",
                value=cpu_percent,
                status=status,
                threshold=self.thresholds["cpu_usage"]["warning"],
                message=message
            )
            
        except Exception as e:
            return HealthMetric(
                name="cpu_usage",
                value=None,
                status=HealthStatus.CRITICAL,
                message=f"Failed to check CPU usage: {e}"
            )
    
    async def _check_memory_usage(self) -> HealthMetric:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            status = HealthStatus.HEALTHY
            message = f"Memory usage: {memory_percent:.1f}% ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)"
            
            if memory_percent >= self.thresholds["memory_usage"]["critical"]:
                status = HealthStatus.CRITICAL
                message = f"CRITICAL: High memory usage at {memory_percent:.1f}%"
            elif memory_percent >= self.thresholds["memory_usage"]["warning"]:
                status = HealthStatus.WARNING
                message = f"WARNING: Elevated memory usage at {memory_percent:.1f}%"
            
            return HealthMetric(
                name="memory_usage",
                value=memory_percent,
                status=status,
                threshold=self.thresholds["memory_usage"]["warning"],
                message=message
            )
            
        except Exception as e:
            return HealthMetric(
                name="memory_usage",
                value=None,
                status=HealthStatus.CRITICAL,
                message=f"Failed to check memory usage: {e}"
            )
    
    async def _check_disk_usage(self) -> HealthMetric:
        """Check disk usage for data directory."""
        try:
            disk_usage = psutil.disk_usage(str(self.data_dir.parent))
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            status = HealthStatus.HEALTHY
            message = f"Disk usage: {disk_percent:.1f}% ({disk_usage.used / 1024**3:.1f}GB / {disk_usage.total / 1024**3:.1f}GB)"
            
            if disk_percent >= self.thresholds["disk_usage"]["critical"]:
                status = HealthStatus.CRITICAL
                message = f"CRITICAL: High disk usage at {disk_percent:.1f}%"
            elif disk_percent >= self.thresholds["disk_usage"]["warning"]:
                status = HealthStatus.WARNING
                message = f"WARNING: Elevated disk usage at {disk_percent:.1f}%"
            
            return HealthMetric(
                name="disk_usage",
                value=disk_percent,
                status=status,
                threshold=self.thresholds["disk_usage"]["warning"],
                message=message
            )
            
        except Exception as e:
            return HealthMetric(
                name="disk_usage",
                value=None,
                status=HealthStatus.CRITICAL,
                message=f"Failed to check disk usage: {e}"
            )
    
    async def _check_api_connectivity(self) -> HealthMetric:
        """Check API connectivity and response time."""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get("https://civitai.com/api/v1/models", 
                                     params={"limit": 1},
                                     timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        status = HealthStatus.HEALTHY
                        message = f"API connectivity: OK ({response_time:.2f}s)"
                        
                        if response_time >= self.thresholds["api_response_time"]["critical"]:
                            status = HealthStatus.CRITICAL
                            message = f"CRITICAL: Slow API response ({response_time:.2f}s)"
                        elif response_time >= self.thresholds["api_response_time"]["warning"]:
                            status = HealthStatus.WARNING
                            message = f"WARNING: Slow API response ({response_time:.2f}s)"
                    else:
                        status = HealthStatus.CRITICAL
                        message = f"CRITICAL: API returned status {response.status}"
                    
                    return HealthMetric(
                        name="api_connectivity",
                        value=response_time,
                        status=status,
                        threshold=self.thresholds["api_response_time"]["warning"],
                        message=message
                    )
                    
        except asyncio.TimeoutError:
            return HealthMetric(
                name="api_connectivity",
                value=None,
                status=HealthStatus.CRITICAL,
                message="CRITICAL: API request timed out"
            )
        except Exception as e:
            return HealthMetric(
                name="api_connectivity",
                value=None,
                status=HealthStatus.CRITICAL,
                message=f"CRITICAL: API connectivity failed: {e}"
            )
    
    async def _check_database_health(self) -> HealthMetric:
        """Check database health and size."""
        try:
            db_path = self.data_dir / "civitai_downloader.db"
            
            if not db_path.exists():
                return HealthMetric(
                    name="database_health",
                    value=0,
                    status=HealthStatus.HEALTHY,
                    message="Database: Not created yet"
                )
            
            # Check database size
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            
            # Check database integrity
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                
                if integrity_result != "ok":
                    return HealthMetric(
                        name="database_health",
                        value=db_size_mb,
                        status=HealthStatus.CRITICAL,
                        message=f"CRITICAL: Database integrity check failed: {integrity_result}"
                    )
                
                # Check if we can perform basic operations
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
            
            status = HealthStatus.HEALTHY
            message = f"Database: OK ({db_size_mb:.1f}MB, {table_count} tables)"
            
            if db_size_mb >= self.thresholds["db_size"]["critical"]:
                status = HealthStatus.CRITICAL
                message = f"CRITICAL: Large database size ({db_size_mb:.1f}MB)"
            elif db_size_mb >= self.thresholds["db_size"]["warning"]:
                status = HealthStatus.WARNING
                message = f"WARNING: Growing database size ({db_size_mb:.1f}MB)"
            
            return HealthMetric(
                name="database_health",
                value=db_size_mb,
                status=status,
                threshold=self.thresholds["db_size"]["warning"],
                message=message
            )
            
        except Exception as e:
            return HealthMetric(
                name="database_health",
                value=None,
                status=HealthStatus.CRITICAL,
                message=f"CRITICAL: Database check failed: {e}"
            )
    
    async def _check_file_permissions(self) -> HealthMetric:
        """Check file system permissions."""
        try:
            test_file = self.data_dir / ".permission_test"
            
            # Test write permissions
            try:
                test_file.write_text("test")
                test_file.unlink()
                
                return HealthMetric(
                    name="file_permissions",
                    value=True,
                    status=HealthStatus.HEALTHY,
                    message="File permissions: OK"
                )
                
            except PermissionError:
                return HealthMetric(
                    name="file_permissions",
                    value=False,
                    status=HealthStatus.CRITICAL,
                    message="CRITICAL: No write permission to data directory"
                )
                
        except Exception as e:
            return HealthMetric(
                name="file_permissions",
                value=None,
                status=HealthStatus.CRITICAL,
                message=f"CRITICAL: Permission check failed: {e}"
            )
    
    async def _check_network_connectivity(self) -> HealthMetric:
        """Check general network connectivity."""
        try:
            # Simple connectivity test
            async with aiohttp.ClientSession() as session:
                async with session.get("https://httpbin.org/status/200",
                                     timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        return HealthMetric(
                            name="network_connectivity",
                            value=True,
                            status=HealthStatus.HEALTHY,
                            message="Network connectivity: OK"
                        )
                    else:
                        return HealthMetric(
                            name="network_connectivity",
                            value=False,
                            status=HealthStatus.WARNING,
                            message=f"WARNING: Network test returned status {response.status}"
                        )
                        
        except Exception as e:
            return HealthMetric(
                name="network_connectivity",
                value=False,
                status=HealthStatus.CRITICAL,
                message=f"CRITICAL: Network connectivity failed: {e}"
            )
    
    def _record_metric_history(self, metric: HealthMetric) -> None:
        """Record metric in history for trend analysis."""
        if metric.name not in self.metric_history:
            self.metric_history[metric.name] = []
        
        self.metric_history[metric.name].append(metric)
        
        # Keep only recent history (last 100 entries)
        if len(self.metric_history[metric.name]) > 100:
            self.metric_history[metric.name] = self.metric_history[metric.name][-100:]
    
    def add_custom_check(self, check_func: Callable[[], HealthMetric]) -> None:
        """Add a custom health check function."""
        self.custom_checks.append(check_func)
    
    def get_metric_trend(self, metric_name: str, window_size: int = 10) -> Optional[str]:
        """
        Get trend for a specific metric.
        
        Args:
            metric_name: Name of the metric
            window_size: Number of recent samples to analyze
            
        Returns:
            Trend description ("improving", "degrading", "stable", or None)
        """
        if metric_name not in self.metric_history:
            return None
        
        history = self.metric_history[metric_name]
        if len(history) < window_size:
            return None
        
        recent_values = [m.value for m in history[-window_size:] if m.value is not None]
        if len(recent_values) < window_size:
            return None
        
        # Simple trend analysis
        first_half = recent_values[:window_size//2]
        second_half = recent_values[window_size//2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        threshold = abs(avg_first) * 0.1  # 10% change threshold
        
        if avg_second > avg_first + threshold:
            return "degrading"  # Values getting worse (higher)
        elif avg_second < avg_first - threshold:
            return "improving"  # Values getting better (lower)
        else:
            return "stable"
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        return {
            "system_uptime": time.time() - self.start_time,
            "thresholds": self.thresholds,
            "metric_trends": {
                name: self.get_metric_trend(name)
                for name in self.metric_history.keys()
            },
            "custom_checks_count": len(self.custom_checks),
            "metric_history_size": {
                name: len(history)
                for name, history in self.metric_history.items()
            }
        }