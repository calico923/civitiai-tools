#!/usr/bin/env python3
"""
Structured Logger for CivitAI Downloader.
Provides JSON-formatted logging with rotation, aggregation, and search capabilities.
"""

import json
import logging
import logging.handlers
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import uuid
import threading
from collections import defaultdict


class StructuredLogger:
    """High-performance structured logger with JSON output and advanced features."""
    
    def __init__(self, log_file: Optional[str] = None, level: str = 'INFO'):
        """
        Initialize structured logger.
        
        Args:
            log_file: Path to log file (None for console only)
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_file = log_file
        self.level = getattr(logging, level.upper())
        self.logger = logging.getLogger(f'civitai_structured_{id(self)}')
        self.logger.setLevel(self.level)
        self.logger.handlers.clear()  # Remove default handlers
        
        # Configure formatters and handlers
        self._configure_handlers()
        
        # Log aggregation cache
        self._log_cache: List[Dict[str, Any]] = []
        self._cache_lock = threading.Lock()
        self._max_cache_size = 10000
        
        # Rotation settings
        self._rotation_config = {
            'max_size_mb': 10,
            'backup_count': 5,
            'rotation_enabled': False
        }
    
    def _configure_handlers(self) -> None:
        """Configure log handlers for structured output."""
        formatter = self._create_json_formatter()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self.level)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(self.level)
            self.logger.addHandler(file_handler)
    
    def _create_json_formatter(self) -> logging.Formatter:
        """Create JSON formatter for structured logging."""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage()
                }
                
                # Add extra fields from record
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                                  'filename', 'module', 'lineno', 'funcName', 'created', 
                                  'msecs', 'relativeCreated', 'thread', 'threadName', 
                                  'processName', 'process', 'stack_info', 'exc_info', 'exc_text']:
                        log_entry[key] = value
                
                return json.dumps(log_entry, default=str)
        
        return JsonFormatter()
    
    def log_structured(self, level: str, message: str, **kwargs) -> None:
        """
        Log structured data with additional fields.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured data fields
        """
        # Create log record with extra fields
        log_level = getattr(logging, level.upper())
        
        # Add structured data to the record
        extra_data = kwargs.copy()
        
        # Create and cache log entry
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level.upper(),
            'message': message,
            **extra_data
        }
        
        with self._cache_lock:
            self._log_cache.append(log_entry)
            if len(self._log_cache) > self._max_cache_size:
                self._log_cache = self._log_cache[-self._max_cache_size//2:]  # Keep recent half
        
        # Log to configured handlers
        self.logger.log(log_level, message, extra=extra_data)
    
    def log_performance(self, operation: str, duration_ms: float, **metadata) -> None:
        """
        Log performance metrics for operations.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            **metadata: Additional performance metadata
        """
        self.log_structured(
            'INFO',
            f'Performance: {operation} completed in {duration_ms:.2f}ms',
            operation=operation,
            duration_ms=duration_ms,
            category='performance',
            **metadata
        )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None, 
                  operation: Optional[str] = None) -> None:
        """
        Log error with context information.
        
        Args:
            error: Exception object
            context: Additional context data
            operation: Operation where error occurred
        """
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'category': 'error'
        }
        
        if context:
            error_data['context'] = context
        
        if operation:
            error_data['operation'] = operation
        
        self.log_structured('ERROR', f'Error in {operation or "unknown"}: {error}', **error_data)
    
    def configure_rotation(self, max_size_mb: int = 10, backup_count: int = 5, 
                          rotation_enabled: bool = True) -> None:
        """
        Configure log rotation.
        
        Args:
            max_size_mb: Maximum size in MB before rotation
            backup_count: Number of backup files to keep
            rotation_enabled: Whether to enable rotation
        """
        self._rotation_config = {
            'max_size_mb': max_size_mb,
            'backup_count': backup_count,
            'rotation_enabled': rotation_enabled
        }
        
        if rotation_enabled and self.log_file:
            # Remove existing file handler
            file_handlers = [h for h in self.logger.handlers if isinstance(h, logging.FileHandler)]
            for handler in file_handlers:
                self.logger.removeHandler(handler)
            
            # Add rotating file handler
            max_bytes = max_size_mb * 1024 * 1024
            rotating_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            rotating_handler.setFormatter(self._create_json_formatter())
            rotating_handler.setLevel(self.level)
            self.logger.addHandler(rotating_handler)
    
    def aggregate_logs(self, start_time: float, group_by: List[str], 
                      metrics: List[str]) -> Dict[str, Any]:
        """
        Aggregate logs within time range.
        
        Args:
            start_time: Start timestamp (unix time)
            group_by: Fields to group by
            metrics: Metrics to calculate
            
        Returns:
            Aggregated log data
        """
        start_datetime = datetime.fromtimestamp(start_time, timezone.utc)
        aggregated = defaultdict(lambda: {
            'count': 0,
            'values': defaultdict(list)
        })
        
        with self._cache_lock:
            for entry in self._log_cache:
                try:
                    entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    if entry_time >= start_datetime:
                        # Create grouping key
                        group_key = tuple(entry.get(field, 'unknown') for field in group_by)
                        if len(group_key) == 1:
                            group_key = group_key[0]
                        
                        aggregated[group_key]['count'] += 1
                        
                        # Collect values for metrics
                        for metric in metrics:
                            if metric.startswith('avg_'):
                                field = metric[4:]  # Remove 'avg_' prefix
                                if field in entry:
                                    aggregated[group_key]['values'][field].append(entry[field])
                            elif metric.startswith('total_'):
                                field = metric[6:]  # Remove 'total_' prefix
                                if field in entry:
                                    aggregated[group_key]['values'][field].append(entry[field])
                
                except (ValueError, KeyError):
                    continue  # Skip malformed entries
        
        # Calculate final metrics
        result = {}
        for group_key, data in aggregated.items():
            result[group_key] = {'count': data['count']}
            
            for metric in metrics:
                if metric.startswith('avg_'):
                    field = metric[4:]
                    values = data['values'].get(field, [])
                    if values and all(isinstance(v, (int, float)) for v in values):
                        result[group_key][metric] = sum(values) / len(values)
                    else:
                        result[group_key][metric] = 0
                        
                elif metric.startswith('total_'):
                    field = metric[6:]
                    values = data['values'].get(field, [])
                    if values and all(isinstance(v, (int, float)) for v in values):
                        result[group_key][metric] = sum(values)
                    else:
                        result[group_key][metric] = 0
        
        return result
    
    def search_logs(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search logs with filters.
        
        Args:
            filters: Filter criteria
            limit: Maximum results to return
            
        Returns:
            Matching log entries
        """
        results = []
        
        with self._cache_lock:
            for entry in reversed(self._log_cache):  # Most recent first
                if len(results) >= limit:
                    break
                
                # Check if entry matches all filters
                matches = True
                for key, value in filters.items():
                    if key not in entry or entry[key] != value:
                        matches = False
                        break
                
                if matches:
                    results.append(entry.copy())
        
        return results


class EnhancedMonitoringService:
    """Integrated monitoring service combining logging, metrics, and alerting."""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize enhanced monitoring service.
        
        Args:
            log_file: Path to log file
        """
        self.logger = StructuredLogger(log_file)
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.operation_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'avg_duration_ms': 0.0
        }
        self._operations_lock = threading.Lock()
    
    def start_operation(self, operation_type: str, **metadata) -> str:
        """
        Start monitoring an operation.
        
        Args:
            operation_type: Type of operation
            **metadata: Operation metadata
            
        Returns:
            Operation ID for tracking
        """
        operation_id = str(uuid.uuid4())
        
        operation_data = {
            'id': operation_id,
            'type': operation_type,
            'start_time': time.time(),
            'status': 'started',
            'progress': 0,
            'metadata': metadata
        }
        
        with self._operations_lock:
            self.active_operations[operation_id] = operation_data
            self.operation_stats['total_operations'] += 1
        
        self.logger.log_structured(
            'INFO',
            f'Operation started: {operation_type}',
            operation_id=operation_id,
            operation_type=operation_type,
            category='operation_lifecycle',
            **metadata
        )
        
        return operation_id
    
    def update_operation_progress(self, operation_id: str, progress: int, 
                                status: Optional[str] = None) -> None:
        """
        Update operation progress.
        
        Args:
            operation_id: Operation ID
            progress: Progress percentage (0-100)
            status: Optional status update
        """
        with self._operations_lock:
            if operation_id in self.active_operations:
                self.active_operations[operation_id]['progress'] = progress
                if status:
                    self.active_operations[operation_id]['status'] = status
                
                self.logger.log_structured(
                    'DEBUG',
                    f'Operation progress: {progress}%',
                    operation_id=operation_id,
                    progress=progress,
                    status=status,
                    category='operation_progress'
                )
    
    def complete_operation(self, operation_id: str, success: bool, 
                         result: Optional[Dict[str, Any]] = None) -> None:
        """
        Complete operation monitoring.
        
        Args:
            operation_id: Operation ID
            success: Whether operation succeeded
            result: Operation result data
        """
        with self._operations_lock:
            if operation_id not in self.active_operations:
                return
            
            operation = self.active_operations[operation_id]
            duration_ms = (time.time() - operation['start_time']) * 1000
            
            # Update stats
            if success:
                self.operation_stats['successful_operations'] += 1
            else:
                self.operation_stats['failed_operations'] += 1
            
            # Update average duration
            total_ops = self.operation_stats['total_operations']
            current_avg = self.operation_stats['avg_duration_ms']
            self.operation_stats['avg_duration_ms'] = (
                (current_avg * (total_ops - 1) + duration_ms) / total_ops
            )
            
            # Log completion
            self.logger.log_structured(
                'INFO',
                f'Operation completed: {operation["type"]}',
                operation_id=operation_id,
                operation_type=operation['type'],
                success=success,
                duration_ms=duration_ms,
                result=result,
                category='operation_lifecycle'
            )
            
            # Remove from active operations
            del self.active_operations[operation_id]
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get operation statistics."""
        with self._operations_lock:
            return self.operation_stats.copy()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for monitoring dashboard.
        
        Returns:
            Dashboard data including current operations and metrics
        """
        with self._operations_lock:
            current_operations = []
            for op_id, op_data in self.active_operations.items():
                current_operations.append({
                    'id': op_id,
                    'type': op_data['type'],
                    'progress': op_data['progress'],
                    'status': op_data['status'],
                    'duration_s': time.time() - op_data['start_time']
                })
        
        # Get recent metrics from logs
        recent_metrics = self.logger.aggregate_logs(
            start_time=time.time() - 3600,  # Last hour
            group_by=['category'],
            metrics=['count']
        )
        
        return {
            'current_operations': current_operations,
            'operation_stats': self.operation_stats.copy(),
            'recent_metrics': recent_metrics,
            'alert_summary': {
                'active_alerts': 0,  # Would integrate with AlertManager
                'recent_alerts': 0
            }
        }