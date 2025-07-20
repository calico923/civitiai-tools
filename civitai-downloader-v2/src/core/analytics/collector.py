#!/usr/bin/env python3
"""
Analytics Data Collector for CivitAI Downloader.
Collects and stores comprehensive analytics data for reporting and analysis.
"""

import asyncio
import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
import statistics
import uuid

try:
    from ...core.config.system_config import SystemConfig
    from ...core.download.manager import DownloadTask, DownloadStatus
    from ...core.search.strategy import SearchResult
    from ...core.security.scanner import ScanReport, ScanResult
    from ...core.bulk.download_manager import BulkDownloadJob, BulkStatus
    from ...core.performance.optimizer import PerformanceMetrics, NetworkCondition
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.config.system_config import SystemConfig
    from core.download.manager import DownloadTask, DownloadStatus
    from core.search.strategy import SearchResult
    from core.security.scanner import ScanReport, ScanResult
    from core.bulk.download_manager import BulkDownloadJob, BulkStatus
    from core.performance.optimizer import PerformanceMetrics, NetworkCondition


class EventType(Enum):
    """Types of analytics events."""
    DOWNLOAD_STARTED = "download_started"
    DOWNLOAD_COMPLETED = "download_completed"
    DOWNLOAD_FAILED = "download_failed"
    DOWNLOAD_CANCELLED = "download_cancelled"
    SEARCH_PERFORMED = "search_performed"
    SECURITY_SCAN = "security_scan"
    BULK_JOB_CREATED = "bulk_job_created"
    BULK_JOB_COMPLETED = "bulk_job_completed"
    PERFORMANCE_SAMPLE = "performance_sample"
    ERROR_OCCURRED = "error_occurred"
    USER_ACTION = "user_action"


@dataclass
class AnalyticsEvent:
    """Individual analytics event."""
    event_id: str
    event_type: EventType
    timestamp: float
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'data': json.dumps(self.data),
            'tags': json.dumps(self.tags),
            'metadata': json.dumps(self.metadata)
        }


@dataclass
class DownloadMetrics:
    """Metrics for download operations."""
    total_downloads: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    cancelled_downloads: int = 0
    total_bytes_downloaded: int = 0
    total_download_time: float = 0.0
    average_download_speed: float = 0.0
    peak_download_speed: float = 0.0
    unique_models_downloaded: int = 0
    unique_creators: int = 0
    
    def success_rate(self) -> float:
        """Calculate download success rate."""
        if self.total_downloads == 0:
            return 0.0
        return (self.successful_downloads / self.total_downloads) * 100
    
    def average_file_size(self) -> float:
        """Calculate average file size."""
        if self.successful_downloads == 0:
            return 0.0
        return self.total_bytes_downloaded / self.successful_downloads


@dataclass
class SearchMetrics:
    """Metrics for search operations."""
    total_searches: int = 0
    total_results_returned: int = 0
    average_results_per_search: float = 0.0
    most_searched_tags: List[Tuple[str, int]] = field(default_factory=list)
    most_downloaded_models: List[Tuple[int, str, int]] = field(default_factory=list)
    search_response_times: List[float] = field(default_factory=list)
    
    def average_response_time(self) -> float:
        """Calculate average search response time."""
        if not self.search_response_times:
            return 0.0
        return statistics.mean(self.search_response_times)


@dataclass
class SecurityMetrics:
    """Metrics for security operations."""
    total_scans: int = 0
    safe_files: int = 0
    suspicious_files: int = 0
    malicious_files: int = 0
    scan_errors: int = 0
    threat_types_detected: Dict[str, int] = field(default_factory=dict)
    average_scan_time: float = 0.0
    
    def threat_detection_rate(self) -> float:
        """Calculate threat detection rate."""
        if self.total_scans == 0:
            return 0.0
        threats = self.suspicious_files + self.malicious_files
        return (threats / self.total_scans) * 100


@dataclass
class PerformanceSnapshot:
    """Performance metrics snapshot."""
    timestamp: float
    cpu_usage: float
    memory_usage: float
    download_speed: float
    active_connections: int
    network_condition: str
    optimization_mode: str


class AnalyticsCollector:
    """Collects and stores analytics data."""
    
    def __init__(self, config: Optional[SystemConfig] = None, db_path: Optional[Path] = None):
        """
        Initialize analytics collector.
        
        Args:
            config: System configuration
            db_path: Path to analytics database
        """
        self.config = config or SystemConfig()
        self.db_path = db_path or Path(self.config.get('analytics.db_path', 'analytics.db'))
        
        # Session tracking
        self.session_id = str(uuid.uuid4())
        self.user_id = self.config.get('analytics.user_id', 'anonymous')
        
        # Event buffer
        self.event_buffer: List[AnalyticsEvent] = []
        self.buffer_size = self.config.get('analytics.buffer_size', 1000)
        self.flush_interval = self.config.get('analytics.flush_interval', 60.0)  # seconds
        
        # Metrics aggregation
        self.download_metrics = DownloadMetrics()
        self.search_metrics = SearchMetrics()
        self.security_metrics = SecurityMetrics()
        self.performance_snapshots: List[PerformanceSnapshot] = []
        
        # State tracking
        self.active_downloads: Dict[str, float] = {}  # task_id -> start_time
        self.model_download_counts: Dict[int, int] = {}
        self.tag_search_counts: Dict[str, int] = {}
        self.creator_counts: Dict[str, int] = {}
        
        # Threading
        self._lock = threading.Lock()
        self._running = False
        self._flush_thread = None
        
        # Initialize database
        self._init_database()
        
        # Start background processing
        self.start()
    
    def _init_database(self):
        """Initialize analytics database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    data TEXT,
                    tags TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS download_sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    total_downloads INTEGER DEFAULT 0,
                    successful_downloads INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    user_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS performance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cpu_usage REAL,
                    memory_usage REAL,
                    download_speed REAL,
                    active_connections INTEGER,
                    network_condition TEXT,
                    optimization_mode TEXT,
                    session_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
                CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_history(timestamp);
            """)
    
    def start(self):
        """Start background analytics processing."""
        if self._running:
            return
        
        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        
        # Record session start
        self.record_event(EventType.USER_ACTION, {
            'action': 'session_started',
            'session_id': self.session_id
        })
    
    def stop(self):
        """Stop analytics processing and flush remaining data."""
        if not self._running:
            return
        
        # Record session end
        self.record_event(EventType.USER_ACTION, {
            'action': 'session_ended',
            'session_id': self.session_id
        })
        
        self._running = False
        
        # Flush remaining events
        self._flush_events()
        
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
    
    def record_event(self, event_type: EventType, data: Dict[str, Any], 
                    tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Record an analytics event.
        
        Args:
            event_type: Type of event
            data: Event data
            tags: Optional tags
            metadata: Optional metadata
        """
        event = AnalyticsEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=time.time(),
            user_id=self.user_id,
            session_id=self.session_id,
            data=data,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        with self._lock:
            self.event_buffer.append(event)
            
            # Update real-time metrics
            self._update_metrics(event)
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.buffer_size:
                self._flush_events()
    
    def record_download_started(self, task: DownloadTask):
        """Record download start event."""
        self.active_downloads[task.id] = time.time()
        
        self.record_event(EventType.DOWNLOAD_STARTED, {
            'task_id': task.id,
            'file_id': task.file_info.id,
            'file_name': task.file_info.name,
            'file_size': task.file_info.size,
            'model_metadata': task.file_info.metadata
        }, tags=['download', 'start'])
    
    def record_download_completed(self, task: DownloadTask):
        """Record download completion event."""
        start_time = self.active_downloads.pop(task.id, time.time())
        duration = time.time() - start_time
        speed = task.file_info.size / duration if duration > 0 else 0
        
        # Update model download counts
        if hasattr(task.file_info, 'metadata') and 'model_id' in task.file_info.metadata:
            model_id = task.file_info.metadata['model_id']
            self.model_download_counts[model_id] = self.model_download_counts.get(model_id, 0) + 1
        
        self.record_event(EventType.DOWNLOAD_COMPLETED, {
            'task_id': task.id,
            'file_id': task.file_info.id,
            'file_name': task.file_info.name,
            'file_size': task.file_info.size,
            'duration': duration,
            'download_speed': speed,
            'final_path': str(task.final_path) if task.final_path else None,
            'model_metadata': task.file_info.metadata
        }, tags=['download', 'success'])
    
    def record_download_failed(self, task: DownloadTask, error: str):
        """Record download failure event."""
        start_time = self.active_downloads.pop(task.id, time.time())
        duration = time.time() - start_time
        
        self.record_event(EventType.DOWNLOAD_FAILED, {
            'task_id': task.id,
            'file_id': task.file_info.id,
            'file_name': task.file_info.name,
            'file_size': task.file_info.size,
            'duration': duration,
            'error': error,
            'model_metadata': task.file_info.metadata
        }, tags=['download', 'failure'])
    
    def record_search_performed(self, query: str, filters: Dict[str, Any], 
                              results: List[SearchResult], response_time: float):
        """Record search operation."""
        # Update tag counts
        if 'tags' in filters:
            for tag in filters['tags']:
                self.tag_search_counts[tag] = self.tag_search_counts.get(tag, 0) + 1
        
        self.record_event(EventType.SEARCH_PERFORMED, {
            'query': query,
            'filters': filters,
            'result_count': len(results),
            'response_time': response_time,
            'model_ids': [result.id for result in results[:10]]  # First 10 IDs
        }, tags=['search'])
    
    def record_security_scan(self, scan_report: ScanReport):
        """Record security scan event."""
        self.record_event(EventType.SECURITY_SCAN, {
            'file_path': str(scan_report.file_path),
            'scan_result': scan_report.scan_result.value,
            'file_type': scan_report.file_type,
            'file_size': scan_report.file_size,
            'scan_duration': scan_report.scan_duration,
            'issues_count': len(scan_report.issues),
            'threat_types': [issue.threat_type.value for issue in scan_report.issues]
        }, tags=['security', 'scan'])
    
    def record_bulk_job_created(self, job: BulkDownloadJob):
        """Record bulk job creation."""
        self.record_event(EventType.BULK_JOB_CREATED, {
            'job_id': job.job_id,
            'job_name': job.name,
            'total_files': job.total_files,
            'total_size': job.total_size,
            'model_count': len(job.search_results),
            'options': job.options
        }, tags=['bulk', 'job', 'created'])
    
    def record_bulk_job_completed(self, job: BulkDownloadJob):
        """Record bulk job completion."""
        duration = job.completed_at - job.started_at if job.completed_at and job.started_at else 0
        
        self.record_event(EventType.BULK_JOB_COMPLETED, {
            'job_id': job.job_id,
            'job_name': job.name,
            'status': job.status.value,
            'total_files': job.total_files,
            'downloaded_files': job.downloaded_files,
            'failed_files': job.failed_files,
            'skipped_files': job.skipped_files,
            'total_size': job.total_size,
            'downloaded_size': job.downloaded_size,
            'duration': duration,
            'success_rate': (job.downloaded_files / job.total_files * 100) if job.total_files > 0 else 0
        }, tags=['bulk', 'job', 'completed'])
    
    def record_performance_sample(self, metrics):
        """Record performance metrics sample."""
        # Handle both PerformanceMetrics objects and Mock objects for testing
        cpu_usage = getattr(metrics, 'cpu_usage', 0.0)
        memory_usage = getattr(metrics, 'memory_usage', 0.0)
        download_speed = getattr(metrics, 'download_speed', 0.0)
        active_connections = getattr(metrics, 'active_connections', 0)
        
        # Handle network_condition attribute which could be Mock or enum
        network_condition = getattr(metrics, 'network_condition', None)
        if hasattr(network_condition, 'value'):
            network_condition_value = network_condition.value
        else:
            network_condition_value = str(network_condition) if network_condition else 'unknown'
        
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            download_speed=download_speed,
            active_connections=active_connections,
            network_condition=network_condition_value,
            optimization_mode='adaptive'  # Could be passed as parameter
        )
        
        with self._lock:
            self.performance_snapshots.append(snapshot)
            # Keep only last 1000 snapshots in memory
            if len(self.performance_snapshots) > 1000:
                self.performance_snapshots = self.performance_snapshots[-1000:]
        
        self.record_event(EventType.PERFORMANCE_SAMPLE, asdict(snapshot), tags=['performance'])
    
    def record_error(self, error_type: str, error_message: str, 
                    context: Optional[Dict[str, Any]] = None):
        """Record error event."""
        self.record_event(EventType.ERROR_OCCURRED, {
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        }, tags=['error'])
    
    def _update_metrics(self, event: AnalyticsEvent):
        """Update aggregated metrics based on event."""
        if event.event_type == EventType.DOWNLOAD_STARTED:
            self.download_metrics.total_downloads += 1
            
        elif event.event_type == EventType.DOWNLOAD_COMPLETED:
            self.download_metrics.successful_downloads += 1
            if 'file_size' in event.data:
                self.download_metrics.total_bytes_downloaded += event.data['file_size']
            if 'duration' in event.data:
                self.download_metrics.total_download_time += event.data['duration']
            if 'download_speed' in event.data:
                self.download_metrics.peak_download_speed = max(
                    self.download_metrics.peak_download_speed,
                    event.data['download_speed']
                )
            
        elif event.event_type == EventType.DOWNLOAD_FAILED:
            self.download_metrics.failed_downloads += 1
            
        elif event.event_type == EventType.DOWNLOAD_CANCELLED:
            self.download_metrics.cancelled_downloads += 1
            
        elif event.event_type == EventType.SEARCH_PERFORMED:
            self.search_metrics.total_searches += 1
            if 'result_count' in event.data:
                self.search_metrics.total_results_returned += event.data['result_count']
            if 'response_time' in event.data:
                self.search_metrics.search_response_times.append(event.data['response_time'])
                
        elif event.event_type == EventType.SECURITY_SCAN:
            self.security_metrics.total_scans += 1
            if 'scan_result' in event.data:
                result = event.data['scan_result']
                if result == 'safe':
                    self.security_metrics.safe_files += 1
                elif result == 'suspicious':
                    self.security_metrics.suspicious_files += 1
                elif result == 'malicious':
                    self.security_metrics.malicious_files += 1
        
        # Update averages
        if self.download_metrics.successful_downloads > 0:
            self.download_metrics.average_download_speed = (
                self.download_metrics.total_bytes_downloaded / 
                self.download_metrics.total_download_time
            ) if self.download_metrics.total_download_time > 0 else 0
            
        if self.search_metrics.total_searches > 0:
            self.search_metrics.average_results_per_search = (
                self.search_metrics.total_results_returned / 
                self.search_metrics.total_searches
            )
    
    def _flush_events(self):
        """Flush buffered events to database."""
        if not self.event_buffer:
            return
        
        events_to_flush = self.event_buffer.copy()
        self.event_buffer.clear()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for event in events_to_flush:
                    conn.execute("""
                        INSERT INTO events (event_id, event_type, timestamp, user_id, 
                                          session_id, data, tags, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id, event.event_type.value, event.timestamp,
                        event.user_id, event.session_id,
                        json.dumps(event.data), json.dumps(event.tags),
                        json.dumps(event.metadata)
                    ))
                
                # Also flush performance snapshots
                if self.performance_snapshots:
                    for snapshot in self.performance_snapshots:
                        conn.execute("""
                            INSERT INTO performance_history (timestamp, cpu_usage, memory_usage,
                                                            download_speed, active_connections,
                                                            network_condition, optimization_mode,
                                                            session_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            snapshot.timestamp, snapshot.cpu_usage, snapshot.memory_usage,
                            snapshot.download_speed, snapshot.active_connections,
                            snapshot.network_condition, snapshot.optimization_mode,
                            self.session_id
                        ))
                    self.performance_snapshots.clear()
                
                conn.commit()
                
        except Exception as e:
            print(f"Error flushing analytics events: {e}")
            # Re-add events to buffer for retry
            self.event_buffer.extend(events_to_flush)
    
    def _flush_loop(self):
        """Background loop for periodic event flushing."""
        while self._running:
            time.sleep(self.flush_interval)
            if self._running:  # Check again after sleep
                with self._lock:
                    self._flush_events()
    
    def get_download_metrics(self) -> DownloadMetrics:
        """Get current download metrics."""
        with self._lock:
            return self.download_metrics
    
    def get_search_metrics(self) -> SearchMetrics:
        """Get current search metrics."""
        with self._lock:
            # Update derived metrics
            self.search_metrics.most_searched_tags = sorted(
                self.tag_search_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            self.search_metrics.most_downloaded_models = sorted(
                [(k, f"Model {k}", v) for k, v in self.model_download_counts.items()],
                key=lambda x: x[2],
                reverse=True
            )[:10]
            
            return self.search_metrics
    
    def get_security_metrics(self) -> SecurityMetrics:
        """Get current security metrics."""
        with self._lock:
            return self.security_metrics
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'download_metrics': asdict(self.get_download_metrics()),
            'search_metrics': asdict(self.get_search_metrics()),
            'security_metrics': asdict(self.get_security_metrics()),
            'event_count': len(self.event_buffer),
            'performance_snapshots': len(self.performance_snapshots)
        }
    
    def query_events(self, event_type: Optional[EventType] = None,
                    start_time: Optional[float] = None,
                    end_time: Optional[float] = None,
                    limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Query analytics events from database.
        
        Args:
            event_type: Filter by event type
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                events = []
                
                for row in cursor.fetchall():
                    event_dict = dict(row)
                    # Parse JSON fields
                    event_dict['data'] = json.loads(event_dict['data'] or '{}')
                    event_dict['tags'] = json.loads(event_dict['tags'] or '[]')
                    event_dict['metadata'] = json.loads(event_dict['metadata'] or '{}')
                    events.append(event_dict)
                
                return events
                
        except Exception as e:
            print(f"Error querying events: {e}")
            return []


# Global collector instance
_global_collector = None

def get_analytics_collector() -> AnalyticsCollector:
    """Get global analytics collector instance."""
    global _global_collector
    if _global_collector is None:
        _global_collector = AnalyticsCollector()
    return _global_collector

def setup_analytics_collector(config: Optional[SystemConfig] = None, 
                            db_path: Optional[Path] = None) -> AnalyticsCollector:
    """Setup global analytics collector."""
    global _global_collector
    _global_collector = AnalyticsCollector(config, db_path)
    return _global_collector


if __name__ == "__main__":
    # Test analytics collector
    print("Testing Analytics Collector...")
    
    collector = AnalyticsCollector()
    
    # Record some test events
    collector.record_event(EventType.USER_ACTION, {
        'action': 'test_started',
        'version': '1.0.0'
    })
    
    collector.record_event(EventType.SEARCH_PERFORMED, {
        'query': 'anime models',
        'result_count': 25,
        'response_time': 0.5
    })
    
    # Get metrics
    download_metrics = collector.get_download_metrics()
    search_metrics = collector.get_search_metrics()
    
    print(f"Download success rate: {download_metrics.success_rate():.1f}%")
    print(f"Search metrics: {search_metrics.total_searches} searches")
    
    # Test querying
    events = collector.query_events(limit=10)
    print(f"Retrieved {len(events)} events")
    
    collector.stop()
    print("Analytics Collector test completed.")