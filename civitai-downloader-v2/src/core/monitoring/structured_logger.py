# src/core/monitoring/structured_logger.py
import logging
import logging.handlers
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from queue import Queue, Empty
import json

from ..interfaces.monitoring import IStructuredLogger, LogLevel

class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Thread-safe rotating file handler with proper error handling."""
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False):
        # Ensure parent directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self._rotation_lock = threading.Lock()
    
    def shouldRollover(self, record):
        """Thread-safe rollover check."""
        with self._rotation_lock:
            return super().shouldRollover(record)
    
    def doRollover(self):
        """Thread-safe rollover with error handling."""
        with self._rotation_lock:
            try:
                super().doRollover()
            except (OSError, IOError) as e:
                # Log rotation failed - continue without rotation
                self.handleError(record=None)

class StructuredLogger(IStructuredLogger):
    """Thread-safe structured logger with robust error handling."""
    
    def __init__(self, name: str = "civitai_downloader", 
                 log_dir: Optional[Path] = None,
                 max_bytes: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        self.name = name
        self.log_dir = log_dir or (Path.home() / ".civitai" / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.log_dir / f"{name}.log"
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # Queue for asynchronous logging
        self._log_queue: Queue = Queue()
        self._worker_thread = None
        self._shutdown_flag = threading.Event()
        self._setup_logger()
        self._start_worker()
    
    def _setup_logger(self):
        """Setup logger with safe handlers."""
        self.logger = logging.getLogger(f"structured_{self.name}")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler with safe rotation
        try:
            file_handler = SafeRotatingFileHandler(
                str(self.log_file),
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(self._get_json_formatter())
            self.logger.addHandler(file_handler)
        except Exception as e:
            # Fallback to console if file handler fails
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self._get_json_formatter())
            self.logger.addHandler(console_handler)
    
    def _get_json_formatter(self):
        """Get JSON formatter for structured logging."""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "logger": record.name
                }
                
                # Add extra fields if present
                if hasattr(record, 'context'):
                    log_data['context'] = record.context
                
                return json.dumps(log_data, ensure_ascii=False)
        
        return JsonFormatter()
    
    def _start_worker(self):
        """Start background worker thread."""
        self._worker_thread = threading.Thread(
            target=self._log_worker,
            name=f"LogWorker-{self.name}",
            daemon=True
        )
        self._worker_thread.start()
    
    def _log_worker(self):
        """Background worker for processing log entries."""
        while not self._shutdown_flag.is_set():
            try:
                # Get log record with timeout
                record = self._log_queue.get(timeout=1.0)
                if record is None:  # Shutdown signal
                    break
                
                # Process the log record
                try:
                    self.logger.handle(record)
                except Exception as e:
                    # Log processing failed - print to stderr as fallback
                    import sys
                    print(f"Logging error: {e}", file=sys.stderr)
                
                self._log_queue.task_done()
                
            except Empty:
                continue  # Timeout - check shutdown flag
    
    def log_structured(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None):
        """Log structured message asynchronously."""
        if self._shutdown_flag.is_set():
            return
        
        # Create log record
        log_level = getattr(logging, level.value.upper(), logging.INFO)
        record = self.logger.makeRecord(
            self.logger.name, log_level, __file__, 0,
            message, (), None
        )
        
        # Add context if provided
        if context:
            record.context = context
        
        # Queue for async processing
        try:
            self._log_queue.put_nowait(record)
        except:
            # Queue full - process synchronously as fallback
            try:
                self.logger.handle(record)
            except:
                pass  # Silent failure to prevent cascading errors
    
    def log_performance(self, operation: str, duration: float, metadata: Optional[Dict[str, Any]] = None):
        """Log performance metrics."""
        context = {
            'operation': operation,
            'duration_ms': duration * 1000,  # Convert to milliseconds
            'performance_metric': True
        }
        if metadata:
            context.update(metadata)
        
        self.log_structured(LogLevel.INFO, f"Performance: {operation} took {duration:.3f}s", context)
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log error with context."""
        error_context = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_log': True
        }
        error_context.update(context)
        
        self.log_structured(LogLevel.ERROR, f"Error: {error}", error_context)
    
    def configure_rotation(self, max_size: int, backup_count: int):
        """Reconfigure log rotation settings."""
        self.max_bytes = max_size
        self.backup_count = backup_count
        
        # Update existing file handlers
        for handler in self.logger.handlers:
            if isinstance(handler, SafeRotatingFileHandler):
                handler.maxBytes = max_size
                handler.backupCount = backup_count
    
    def shutdown(self):
        """Graceful shutdown of logger."""
        self._shutdown_flag.set()
        
        # Signal worker to stop
        self._log_queue.put(None)
        
        # Wait for worker to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        
        # Close handlers
        for handler in self.logger.handlers:
            handler.close()