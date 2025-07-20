#!/usr/bin/env python3
"""
Alert Manager for CivitAI Downloader.
Provides threshold-based alerting with notification handling and alert suppression.
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class AlertThreshold:
    """Alert threshold configuration."""
    warning: float
    critical: float


@dataclass
class Alert:
    """Alert instance."""
    metric: str
    alert_type: str  # 'warning' or 'critical'
    value: float
    threshold: float
    timestamp: float
    message: str


class AlertManager:
    """Advanced alert manager with threshold monitoring and notification handling."""
    
    def __init__(self, suppression_window_seconds: int = 300):
        """
        Initialize alert manager.
        
        Args:
            suppression_window_seconds: Time window to suppress duplicate alerts
        """
        self.suppression_window = suppression_window_seconds
        self.thresholds: Dict[str, AlertThreshold] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.last_alert_time: Dict[str, float] = defaultdict(float)
        
        # Notification handling
        self.notification_handlers: List[Callable] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Alert statistics
        self.alert_stats = {
            'total_alerts': 0,
            'warning_alerts': 0,
            'critical_alerts': 0,
            'suppressed_alerts': 0
        }
    
    def configure_thresholds(self, threshold_config: Dict[str, Dict[str, float]]) -> None:
        """
        Configure alert thresholds for metrics.
        
        Args:
            threshold_config: Dict mapping metric names to threshold configurations
                Format: {'metric_name': {'warning': value, 'critical': value}}
        """
        with self._lock:
            for metric, config in threshold_config.items():
                if 'warning' in config and 'critical' in config:
                    self.thresholds[metric] = AlertThreshold(
                        warning=config['warning'],
                        critical=config['critical']
                    )
    
    def set_notification_handler(self, handler: Callable[[str, str, float, float], None]) -> None:
        """
        Set notification handler for alerts.
        
        Args:
            handler: Function that takes (alert_type, metric, value, threshold)
        """
        with self._lock:
            self.notification_handlers = [handler]
    
    def add_notification_handler(self, handler: Callable[[str, str, float, float], None]) -> None:
        """
        Add notification handler for alerts.
        
        Args:
            handler: Function that takes (alert_type, metric, value, threshold)
        """
        with self._lock:
            self.notification_handlers.append(handler)
    
    def check_metric(self, metric: str, value: float) -> Optional[Alert]:
        """
        Check metric value against thresholds and trigger alerts if needed.
        
        Args:
            metric: Metric name
            value: Current metric value
            
        Returns:
            Alert instance if triggered, None otherwise
        """
        if metric not in self.thresholds:
            return None
        
        threshold = self.thresholds[metric]
        alert_type = None
        threshold_value = None
        
        # Determine alert level
        if value >= threshold.critical:
            alert_type = 'critical'
            threshold_value = threshold.critical
        elif value >= threshold.warning:
            alert_type = 'warning'
            threshold_value = threshold.warning
        else:
            # Value is normal, clear any active alerts for this metric
            with self._lock:
                if metric in self.active_alerts:
                    del self.active_alerts[metric]
            return None
        
        # Check alert suppression
        alert_key = f"{metric}_{alert_type}"
        current_time = time.time()
        
        with self._lock:
            last_alert = self.last_alert_time.get(alert_key, 0)
            
            if current_time - last_alert < self.suppression_window:
                # Suppress duplicate alert
                self.alert_stats['suppressed_alerts'] += 1
                return None
            
            # Create new alert
            alert = Alert(
                metric=metric,
                alert_type=alert_type,
                value=value,
                threshold=threshold_value,
                timestamp=current_time,
                message=f"{metric} {alert_type}: {value} exceeds threshold {threshold_value}"
            )
            
            # Update tracking
            self.active_alerts[metric] = alert
            self.alert_history.append(alert)
            self.last_alert_time[alert_key] = current_time
            
            # Update statistics
            self.alert_stats['total_alerts'] += 1
            if alert_type == 'warning':
                self.alert_stats['warning_alerts'] += 1
            else:
                self.alert_stats['critical_alerts'] += 1
            
            # Limit history size
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-500:]  # Keep recent half
        
        # Send notifications
        self._notify_handlers(alert_type, metric, value, threshold_value)
        
        return alert
    
    def get_active_alerts(self) -> List[Alert]:
        """
        Get list of currently active alerts.
        
        Returns:
            List of active alerts
        """
        with self._lock:
            return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """
        Get recent alert history.
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent alerts
        """
        with self._lock:
            return self.alert_history[-limit:] if self.alert_history else []
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """
        Get alert statistics.
        
        Returns:
            Alert statistics
        """
        with self._lock:
            return {
                **self.alert_stats.copy(),
                'active_alert_count': len(self.active_alerts),
                'configured_metrics': len(self.thresholds),
                'notification_handlers': len(self.notification_handlers)
            }
    
    def clear_alerts(self, metric: Optional[str] = None) -> None:
        """
        Clear alerts for a specific metric or all metrics.
        
        Args:
            metric: Metric name to clear, or None to clear all
        """
        with self._lock:
            if metric:
                if metric in self.active_alerts:
                    del self.active_alerts[metric]
            else:
                self.active_alerts.clear()
    
    def get_metric_status(self, metric: str) -> Dict[str, Any]:
        """
        Get current status of a metric.
        
        Args:
            metric: Metric name
            
        Returns:
            Metric status information
        """
        with self._lock:
            status = {
                'metric': metric,
                'has_thresholds': metric in self.thresholds,
                'active_alert': metric in self.active_alerts,
                'last_alert_time': self.last_alert_time.get(f"{metric}_warning", 0)
            }
            
            if metric in self.thresholds:
                status['thresholds'] = {
                    'warning': self.thresholds[metric].warning,
                    'critical': self.thresholds[metric].critical
                }
            
            if metric in self.active_alerts:
                alert = self.active_alerts[metric]
                status['current_alert'] = {
                    'type': alert.alert_type,
                    'value': alert.value,
                    'threshold': alert.threshold,
                    'timestamp': alert.timestamp
                }
        
        return status
    
    def configure_suppression(self, window_seconds: int) -> None:
        """
        Configure alert suppression window.
        
        Args:
            window_seconds: Suppression window in seconds
        """
        with self._lock:
            self.suppression_window = window_seconds
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get summary data for monitoring dashboard.
        
        Returns:
            Dashboard summary data
        """
        current_time = time.time()
        
        with self._lock:
            # Count alerts by severity
            critical_count = sum(1 for alert in self.active_alerts.values() 
                               if alert.alert_type == 'critical')
            warning_count = sum(1 for alert in self.active_alerts.values() 
                              if alert.alert_type == 'warning')
            
            # Recent alerts (last hour)
            recent_alerts = [
                alert for alert in self.alert_history
                if current_time - alert.timestamp < 3600
            ]
            
            # Most frequent alerting metrics
            metric_counts = defaultdict(int)
            for alert in self.alert_history[-100:]:  # Last 100 alerts
                metric_counts[alert.metric] += 1
            
            top_metrics = sorted(metric_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'alert_summary': {
                'total_active': len(self.active_alerts),
                'critical_active': critical_count,
                'warning_active': warning_count,
                'recent_alerts_1h': len(recent_alerts),
                'suppression_window_s': self.suppression_window
            },
            'top_alerting_metrics': top_metrics,
            'alert_statistics': self.get_alert_stats()
        }
    
    def _notify_handlers(self, alert_type: str, metric: str, value: float, threshold: float) -> None:
        """
        Notify all registered handlers about an alert.
        
        Args:
            alert_type: Type of alert ('warning' or 'critical')
            metric: Metric name
            value: Current value
            threshold: Threshold that was exceeded
        """
        for handler in self.notification_handlers:
            try:
                handler(alert_type, metric, value, threshold)
            except Exception:
                # Don't let notification failures break alert processing
                pass