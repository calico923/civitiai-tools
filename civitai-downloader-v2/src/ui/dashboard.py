#!/usr/bin/env python3
"""
Dashboard System.
Implements requirement 20.1: Real-time dashboard with system metrics and status.
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import sys
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    PERCENTAGE = "percentage"
    RATE = "rate"
    STATUS = "status"
    HISTOGRAM = "histogram"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """Metric value with metadata."""
    value: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age_seconds(self) -> float:
        """Age of the metric in seconds."""
        return time.time() - self.timestamp


@dataclass
class MetricCard:
    """Dashboard metric card."""
    card_id: str
    title: str
    metric_type: MetricType
    current_value: Optional[MetricValue] = None
    history: List[MetricValue] = field(default_factory=list)
    unit: Optional[str] = None
    format_string: Optional[str] = None
    alert_thresholds: Dict[AlertLevel, float] = field(default_factory=dict)
    trend_window_minutes: int = 10
    
    def update_value(self, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update metric value."""
        metric_value = MetricValue(
            value=value,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        self.current_value = metric_value
        self.history.append(metric_value)
        
        # Keep history within trend window
        cutoff_time = time.time() - (self.trend_window_minutes * 60)
        self.history = [mv for mv in self.history if mv.timestamp > cutoff_time]
    
    def get_trend(self) -> str:
        """Calculate trend from history."""
        if len(self.history) < 2:
            return "stable"
        
        # Compare first half with second half
        mid_point = len(self.history) // 2
        first_half = self.history[:mid_point]
        second_half = self.history[mid_point:]
        
        if not first_half or not second_half:
            return "stable"
        
        first_avg = sum(mv.value for mv in first_half if isinstance(mv.value, (int, float))) / len(first_half)
        second_avg = sum(mv.value for mv in second_half if isinstance(mv.value, (int, float))) / len(second_half)
        
        if abs(second_avg - first_avg) < 0.01:
            return "stable"
        elif second_avg > first_avg:
            return "increasing"
        else:
            return "decreasing"
    
    def get_alert_level(self) -> Optional[AlertLevel]:
        """Get current alert level based on thresholds."""
        if not self.current_value or not isinstance(self.current_value.value, (int, float)):
            return None
        
        value = self.current_value.value
        
        if AlertLevel.CRITICAL in self.alert_thresholds and value >= self.alert_thresholds[AlertLevel.CRITICAL]:
            return AlertLevel.CRITICAL
        elif AlertLevel.WARNING in self.alert_thresholds and value >= self.alert_thresholds[AlertLevel.WARNING]:
            return AlertLevel.WARNING
        else:
            return AlertLevel.INFO
    
    def format_value(self) -> str:
        """Format current value for display."""
        if not self.current_value:
            return "N/A"
        
        value = self.current_value.value
        
        if self.format_string:
            return self.format_string.format(value)
        elif self.metric_type == MetricType.PERCENTAGE:
            return f"{value:.1f}%"
        elif self.unit:
            return f"{value} {self.unit}"
        else:
            return str(value)


@dataclass
class DashboardWidget:
    """Dashboard widget container."""
    widget_id: str
    title: str
    widget_type: str  # "metrics", "chart", "table", "log", "status"
    position: tuple[int, int]  # (row, column)
    size: tuple[int, int]  # (height, width)
    metrics: List[MetricCard] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 5  # seconds
    enabled: bool = True
    
    def add_metric(self, metric: MetricCard) -> None:
        """Add metric to widget."""
        self.metrics.append(metric)
    
    def get_metric(self, card_id: str) -> Optional[MetricCard]:
        """Get metric by ID."""
        return next((m for m in self.metrics if m.card_id == card_id), None)
    
    def update_data(self, data: Dict[str, Any]) -> None:
        """Update widget data."""
        self.data.update(data)


class Dashboard:
    """
    Real-time dashboard system.
    Implements requirement 20.1: Comprehensive system monitoring dashboard.
    """
    
    def __init__(self, title: str = "CivitAI Downloader Dashboard"):
        """
        Initialize dashboard.
        
        Args:
            title: Dashboard title
        """
        self.title = title
        self.widgets: Dict[str, DashboardWidget] = {}
        self.metrics: Dict[str, MetricCard] = {}
        self.alerts: List[Dict[str, Any]] = []
        
        # Dashboard state
        self.running = False
        self.refresh_thread: Optional[threading.Thread] = None
        self.update_callbacks: Dict[str, List[Callable]] = {}
        
        # Display configuration
        self.grid_rows = 20
        self.grid_cols = 80
        self.refresh_interval = 1.0  # seconds
        
        # Color scheme
        self.colors = {
            'border': '\033[94m',      # Blue
            'title': '\033[1;96m',     # Bright Cyan
            'success': '\033[92m',     # Green
            'warning': '\033[93m',     # Yellow
            'critical': '\033[91m',    # Red
            'info': '\033[96m',        # Cyan
            'dim': '\033[2m',          # Dim
            'reset': '\033[0m'         # Reset
        }
        
        # Initialize default widgets
        self._create_default_widgets()
    
    def _create_default_widgets(self) -> None:
        """Create default dashboard widgets."""
        # System metrics widget
        system_widget = DashboardWidget(
            widget_id="system_metrics",
            title="System Metrics",
            widget_type="metrics",
            position=(0, 0),
            size=(8, 40)
        )
        
        # Add system metrics
        system_widget.add_metric(MetricCard(
            card_id="cpu_usage",
            title="CPU Usage",
            metric_type=MetricType.PERCENTAGE,
            unit="%",
            alert_thresholds={AlertLevel.WARNING: 80, AlertLevel.CRITICAL: 95}
        ))
        
        system_widget.add_metric(MetricCard(
            card_id="memory_usage", 
            title="Memory Usage",
            metric_type=MetricType.PERCENTAGE,
            unit="%",
            alert_thresholds={AlertLevel.WARNING: 85, AlertLevel.CRITICAL: 95}
        ))
        
        system_widget.add_metric(MetricCard(
            card_id="disk_usage",
            title="Disk Usage", 
            metric_type=MetricType.PERCENTAGE,
            unit="%",
            alert_thresholds={AlertLevel.WARNING: 85, AlertLevel.CRITICAL: 95}
        ))
        
        self.add_widget(system_widget)
        
        # Download metrics widget
        download_widget = DashboardWidget(
            widget_id="download_metrics",
            title="Download Status",
            widget_type="metrics",
            position=(0, 40),
            size=(8, 40)
        )
        
        download_widget.add_metric(MetricCard(
            card_id="active_downloads",
            title="Active Downloads",
            metric_type=MetricType.COUNTER,
            unit="files"
        ))
        
        download_widget.add_metric(MetricCard(
            card_id="download_rate",
            title="Download Rate",
            metric_type=MetricType.RATE,
            unit="MB/s"
        ))
        
        download_widget.add_metric(MetricCard(
            card_id="total_downloaded",
            title="Total Downloaded",
            metric_type=MetricType.COUNTER,
            unit="MB"
        ))
        
        self.add_widget(download_widget)
        
        # Security status widget
        security_widget = DashboardWidget(
            widget_id="security_status",
            title="Security Status",
            widget_type="status",
            position=(8, 0),
            size=(6, 80)
        )
        
        self.add_widget(security_widget)
        
        # Recent activity widget
        activity_widget = DashboardWidget(
            widget_id="recent_activity",
            title="Recent Activity",
            widget_type="log",
            position=(14, 0),
            size=(6, 80)
        )
        
        self.add_widget(activity_widget)
    
    def add_widget(self, widget: DashboardWidget) -> None:
        """Add widget to dashboard."""
        self.widgets[widget.widget_id] = widget
        
        # Register metrics
        for metric in widget.metrics:
            self.metrics[metric.card_id] = metric
    
    def update_metric(self, card_id: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update metric value.
        
        Args:
            card_id: Metric card ID
            value: New value
            metadata: Optional metadata
        """
        if card_id in self.metrics:
            self.metrics[card_id].update_value(value, metadata)
            
            # Check for alerts
            self._check_metric_alerts(card_id)
            
            # Notify callbacks
            self._notify_callbacks(card_id, value)
    
    def _check_metric_alerts(self, card_id: str) -> None:
        """Check metric for alert conditions."""
        metric = self.metrics[card_id]
        alert_level = metric.get_alert_level()
        
        if alert_level and alert_level in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
            alert = {
                'timestamp': time.time(),
                'level': alert_level.value,
                'metric_id': card_id,
                'title': f"{metric.title} Alert",
                'message': f"{metric.title}: {metric.format_value()}",
                'value': metric.current_value.value if metric.current_value else None
            }
            
            self.alerts.append(alert)
            
            # Keep only recent alerts (last 100)
            self.alerts = self.alerts[-100:]
    
    def start_dashboard(self) -> None:
        """Start dashboard refresh loop."""
        if self.running:
            return
        
        self.running = True
        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
        
        logger.info("Dashboard started")
    
    def stop_dashboard(self) -> None:
        """Stop dashboard refresh."""
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=2.0)
        
        logger.info("Dashboard stopped")
    
    def _refresh_loop(self) -> None:
        """Main dashboard refresh loop."""
        while self.running:
            try:
                self._refresh_display()
                time.sleep(self.refresh_interval)
            except Exception as e:
                logger.error(f"Dashboard refresh error: {e}")
                time.sleep(5.0)  # Longer delay on error
    
    def _refresh_display(self) -> None:
        """Refresh dashboard display."""
        # Clear screen
        print('\033[2J\033[H', end='')
        
        # Render dashboard
        self._render_header()
        self._render_widgets()
        self._render_alerts()
        
        sys.stdout.flush()
    
    def _render_header(self) -> None:
        """Render dashboard header."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Title bar
        title_line = f" {self.title} "
        time_line = f" {current_time} "
        
        width = self.grid_cols
        padding = width - len(title_line) - len(time_line)
        
        header = f"{self.colors['title']}{title_line}{'─' * padding}{time_line}{self.colors['reset']}"
        print(header)
        print("─" * width)
    
    def _render_widgets(self) -> None:
        """Render all dashboard widgets."""
        for widget in self.widgets.values():
            if not widget.enabled:
                continue
            
            self._render_widget(widget)
    
    def _render_widget(self, widget: DashboardWidget) -> None:
        """Render individual widget."""
        if widget.widget_type == "metrics":
            self._render_metrics_widget(widget)
        elif widget.widget_type == "status":
            self._render_status_widget(widget)
        elif widget.widget_type == "log":
            self._render_log_widget(widget)
        elif widget.widget_type == "table":
            self._render_table_widget(widget)
    
    def _render_metrics_widget(self, widget: DashboardWidget) -> None:
        """Render metrics widget."""
        # Widget border and title
        border_char = "│"
        corner_tl = "┌"
        corner_tr = "┐"
        corner_bl = "└"
        corner_br = "┘"
        horizontal = "─"
        
        width = widget.size[1]
        
        # Top border with title
        title_line = f"{corner_tl}{horizontal * 2} {widget.title} {horizontal * (width - len(widget.title) - 6)}{corner_tr}"
        print(f"{self.colors['border']}{title_line}{self.colors['reset']}")
        
        # Metrics content
        for metric in widget.metrics:
            if not metric.current_value:
                value_display = "N/A"
                trend_display = ""
                color = self.colors['dim']
            else:
                value_display = metric.format_value()
                trend = metric.get_trend()
                trend_symbols = {
                    'increasing': '↗',
                    'decreasing': '↘', 
                    'stable': '→'
                }
                trend_display = f" {trend_symbols.get(trend, '?')}"
                
                # Color based on alert level
                alert_level = metric.get_alert_level()
                if alert_level == AlertLevel.CRITICAL:
                    color = self.colors['critical']
                elif alert_level == AlertLevel.WARNING:
                    color = self.colors['warning']
                else:
                    color = self.colors['success']
            
            # Format metric line
            metric_name = metric.title[:20].ljust(20)
            value_text = f"{value_display}{trend_display}"
            padding = width - len(metric_name) - len(value_text) - 4
            
            metric_line = f"{border_char} {metric_name} {'·' * padding} {color}{value_text}{self.colors['reset']} {border_char}"
            print(metric_line)
        
        # Fill remaining space if needed
        content_lines = len(widget.metrics) + 2  # +2 for top/bottom borders
        for _ in range(max(0, widget.size[0] - content_lines)):
            empty_line = f"{border_char}{' ' * (width-2)}{border_char}"
            print(empty_line)
        
        # Bottom border
        bottom_line = f"{corner_bl}{horizontal * (width-2)}{corner_br}"
        print(f"{self.colors['border']}{bottom_line}{self.colors['reset']}")
    
    def _render_status_widget(self, widget: DashboardWidget) -> None:
        """Render status widget."""
        width = widget.size[1]
        
        # Header
        print(f"{self.colors['border']}┌─ {widget.title} {'─' * (width - len(widget.title) - 4)}┐{self.colors['reset']}")
        
        # Status items from widget data
        status_items = widget.data.get('status_items', [])
        
        if not status_items:
            # Default status items
            status_items = [
                {'name': 'API Connection', 'status': 'connected', 'details': 'CivitAI API responding'},
                {'name': 'Database', 'status': 'healthy', 'details': 'SQLite operational'},
                {'name': 'Security Scan', 'status': 'active', 'details': 'Real-time scanning enabled'},
                {'name': 'Download Queue', 'status': 'idle', 'details': 'No active downloads'}
            ]
        
        for item in status_items:
            name = item['name'][:25].ljust(25)
            status = item['status']
            details = item.get('details', '')
            
            # Status indicator
            status_colors = {
                'connected': self.colors['success'],
                'healthy': self.colors['success'],
                'active': self.colors['info'],
                'idle': self.colors['dim'],
                'warning': self.colors['warning'],
                'error': self.colors['critical'],
                'disconnected': self.colors['critical']
            }
            
            status_color = status_colors.get(status, self.colors['dim'])
            status_text = f"{status_color}●{self.colors['reset']} {status.upper()}"
            
            # Format line
            remaining_width = width - len(name) - len(status) - 8
            details_text = details[:remaining_width] if details else ""
            
            line = f"│ {name} {status_text} {details_text.ljust(remaining_width)} │"
            print(line)
        
        # Fill remaining space
        content_lines = len(status_items) + 2
        for _ in range(max(0, widget.size[0] - content_lines)):
            print(f"│{' ' * (width-2)}│")
        
        # Bottom border
        print(f"{self.colors['border']}└{'─' * (width-2)}┘{self.colors['reset']}")
    
    def _render_log_widget(self, widget: DashboardWidget) -> None:
        """Render log widget."""
        width = widget.size[1]
        height = widget.size[0]
        
        # Header
        print(f"{self.colors['border']}┌─ {widget.title} {'─' * (width - len(widget.title) - 4)}┐{self.colors['reset']}")
        
        # Log entries from widget data
        log_entries = widget.data.get('log_entries', [])
        
        # Show most recent entries that fit
        max_entries = height - 2
        recent_entries = log_entries[-max_entries:] if log_entries else []
        
        for entry in recent_entries:
            timestamp = entry.get('timestamp', time.time())
            level = entry.get('level', 'INFO')
            message = entry.get('message', 'No message')
            
            # Format timestamp
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime("%H:%M:%S")
            
            # Level color
            level_colors = {
                'DEBUG': self.colors['dim'],
                'INFO': self.colors['info'],
                'WARNING': self.colors['warning'],
                'ERROR': self.colors['critical'],
                'CRITICAL': self.colors['critical']
            }
            level_color = level_colors.get(level, self.colors['reset'])
            
            # Format message to fit
            max_message_len = width - 15  # Account for borders, timestamp, level
            if len(message) > max_message_len:
                message = message[:max_message_len-3] + "..."
            
            log_line = f"│{time_str} {level_color}{level[:4]:4}{self.colors['reset']} {message.ljust(max_message_len)}│"
            print(log_line)
        
        # Fill remaining space
        used_lines = len(recent_entries) + 2
        for _ in range(max(0, height - used_lines)):
            print(f"│{' ' * (width-2)}│")
        
        # Bottom border
        print(f"{self.colors['border']}└{'─' * (width-2)}┘{self.colors['reset']}")
    
    def _render_table_widget(self, widget: DashboardWidget) -> None:
        """Render table widget."""
        width = widget.size[1]
        
        # Header
        print(f"{self.colors['border']}┌─ {widget.title} {'─' * (width - len(widget.title) - 4)}┐{self.colors['reset']}")
        
        # Table data
        headers = widget.data.get('headers', [])
        rows = widget.data.get('rows', [])
        
        if headers and rows:
            # Calculate column widths
            col_count = len(headers)
            col_width = (width - col_count - 1) // col_count
            
            # Header row
            header_line = "│"
            for header in headers:
                header_text = str(header)[:col_width-1].ljust(col_width-1)
                header_line += f"{self.colors['title']}{header_text}{self.colors['reset']}│"
            print(header_line)
            
            # Separator
            separator = "├" + "┼".join("─" * col_width for _ in headers) + "┤"
            print(separator)
            
            # Data rows
            max_rows = widget.size[0] - 4  # Account for header, separator, borders
            for row in rows[:max_rows]:
                row_line = "│"
                for i, cell in enumerate(row[:col_count]):
                    cell_text = str(cell)[:col_width-1].ljust(col_width-1)
                    row_line += f"{cell_text}│"
                print(row_line)
        else:
            # No data message
            no_data_line = f"│{'No data available'.center(width-2)}│"
            print(no_data_line)
        
        # Fill remaining space
        content_height = min(len(rows) + 3, widget.size[0] - 1) if headers and rows else 2
        for _ in range(max(0, widget.size[0] - content_height - 1)):
            print(f"│{' ' * (width-2)}│")
        
        # Bottom border
        print(f"{self.colors['border']}└{'─' * (width-2)}┘{self.colors['reset']}")
    
    def _render_alerts(self) -> None:
        """Render alerts section."""
        if not self.alerts:
            return
        
        print("\n" + self.colors['warning'] + "🚨 ALERTS:" + self.colors['reset'])
        
        # Show recent alerts (last 5)
        recent_alerts = self.alerts[-5:]
        
        for alert in recent_alerts:
            level = alert['level']
            title = alert['title']
            message = alert['message']
            timestamp = datetime.fromtimestamp(alert['timestamp']).strftime("%H:%M:%S")
            
            level_colors = {
                'warning': self.colors['warning'],
                'critical': self.colors['critical'],
                'info': self.colors['info']
            }
            
            color = level_colors.get(level, self.colors['reset'])
            print(f"  {color}[{timestamp}] {level.upper()}: {title} - {message}{self.colors['reset']}")
    
    def register_callback(self, metric_id: str, callback: Callable) -> None:
        """Register callback for metric updates."""
        if metric_id not in self.update_callbacks:
            self.update_callbacks[metric_id] = []
        self.update_callbacks[metric_id].append(callback)
    
    def _notify_callbacks(self, metric_id: str, value: Any) -> None:
        """Notify registered callbacks."""
        callbacks = self.update_callbacks.get(metric_id, [])
        for callback in callbacks:
            try:
                callback(metric_id, value)
            except Exception as e:
                logger.error(f"Callback error for metric {metric_id}: {e}")
    
    def update_widget_data(self, widget_id: str, data: Dict[str, Any]) -> None:
        """Update widget data."""
        if widget_id in self.widgets:
            self.widgets[widget_id].update_data(data)
    
    def add_log_entry(self, level: str, message: str, widget_id: str = "recent_activity") -> None:
        """Add log entry to log widget."""
        if widget_id in self.widgets:
            widget = self.widgets[widget_id]
            
            if 'log_entries' not in widget.data:
                widget.data['log_entries'] = []
            
            entry = {
                'timestamp': time.time(),
                'level': level,
                'message': message
            }
            
            widget.data['log_entries'].append(entry)
            
            # Keep only recent entries (last 100)
            widget.data['log_entries'] = widget.data['log_entries'][-100:]
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary data."""
        return {
            'title': self.title,
            'widgets': len(self.widgets),
            'metrics': len(self.metrics),
            'alerts': len(self.alerts),
            'running': self.running,
            'last_update': time.time()
        }
    
    @staticmethod
    def create_system_dashboard() -> 'Dashboard':
        """Create pre-configured system monitoring dashboard."""
        dashboard = Dashboard("System Monitor")
        
        # Additional system metrics
        dashboard.update_metric('network_status', 'connected')
        dashboard.update_metric('api_response_time', 150)
        
        return dashboard
    
    @staticmethod
    def create_download_dashboard() -> 'Dashboard':
        """Create pre-configured download monitoring dashboard."""
        dashboard = Dashboard("Download Monitor")
        
        # Download-specific widgets
        queue_widget = DashboardWidget(
            widget_id="download_queue",
            title="Download Queue",
            widget_type="table",
            position=(8, 0),
            size=(8, 80)
        )
        
        queue_widget.data = {
            'headers': ['Model', 'Progress', 'Speed', 'ETA'],
            'rows': []
        }
        
        dashboard.add_widget(queue_widget)
        
        return dashboard