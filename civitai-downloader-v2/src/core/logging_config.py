"""
Centralized logging configuration for CivitAI Downloader v2.
Provides file-based logging with rotation and proper formatting.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import sys
import os


class FileLoggingFilter(logging.Filter):
    """Filter to redirect debug logs to files only."""
    def filter(self, record):
        # Only allow INFO and above to go to console
        return record.levelno >= logging.INFO if hasattr(record, '_console') else True


class ConsoleFilter(logging.Filter):
    """Filter for console output - only show WARNING and above."""
    def filter(self, record):
        return record.levelno >= logging.WARNING


def setup_logging(
    log_dir: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    log_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Setup centralized logging configuration with daily rotation.
    
    Args:
        log_dir: Directory for log files (default: /Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/logs)
        console_level: Logging level for console output
        file_level: Logging level for file output
        log_name: Custom log file name prefix
        
    Returns:
        Dict containing log file paths and logger configuration
    """
    # Set default log directory
    if log_dir is None:
        log_dir = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/logs")
    
    # Create log directory if it doesn't exist
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate log file names (without timestamp for TimedRotatingFileHandler)
    log_prefix = log_name or "civitai"
    
    # Log file paths (base names for rotation)
    debug_log = log_dir / f"{log_prefix}_debug.log"
    error_log = log_dir / f"{log_prefix}_error.log"
    
    # Remove all existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler (WARNING and above only)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(max(console_level, logging.WARNING))  # Minimum WARNING level
    console_handler.setFormatter(simple_formatter)
    console_handler.addFilter(ConsoleFilter())
    
    # Debug file handler (all levels) - daily rotation
    debug_file_handler = logging.handlers.TimedRotatingFileHandler(
        debug_log,
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding='utf-8'
    )
    debug_file_handler.setLevel(file_level)
    debug_file_handler.setFormatter(detailed_formatter)
    debug_file_handler.suffix = "%Y%m%d"  # Add date suffix to rotated files
    
    # Error file handler (ERROR and above) - daily rotation
    error_file_handler = logging.handlers.TimedRotatingFileHandler(
        error_log,
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    error_file_handler.suffix = "%Y%m%d"  # Add date suffix to rotated files
    
    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(debug_file_handler)
    root_logger.addHandler(error_file_handler)
    
    # Redirect print statements that look like debug output
    _redirect_debug_prints()
    
    # Log initial message (to file only)
    file_logger = logging.getLogger('logging_init')
    file_logger.info(f"Logging initialized - Debug: {debug_log}, Error: {error_log}")
    
    return {
        'debug_log': debug_log,
        'error_log': error_log,
        'log_dir': log_dir,
        'handlers': {
            'console': console_handler,
            'debug_file': debug_file_handler,
            'error_file': error_file_handler
        }
    }


def _redirect_debug_prints():
    """Redirect debug print statements to logging."""
    class DebugPrintLogger:
        def __init__(self, logger, level):
            self.logger = logger
            self.level = level
            self.buffer = ''
            
        def write(self, message):
            if message and message != '\n':
                # Handle both string and bytes
                if isinstance(message, bytes):
                    message = message.decode('utf-8', errors='replace')
                # Check if this looks like a debug print
                if any(keyword in message.upper() for keyword in ['DEBUG', 'TRACE', 'VERBOSE']):
                    self.logger.log(self.level, message.rstrip())
                else:
                    # Let normal prints go through
                    sys.__stdout__.write(message)
                    
        def flush(self):
            if self.buffer:
                self.write(self.buffer)
                self.buffer = ''
            sys.__stdout__.flush()
    
    # Only redirect if not already redirected
    if not isinstance(sys.stdout, DebugPrintLogger):
        debug_logger = logging.getLogger('debug_prints')
        sys.stdout = DebugPrintLogger(debug_logger, logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_log_level(level: str, logger_name: Optional[str] = None):
    """
    Set logging level for a specific logger or all loggers.
    
    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        logger_name: Optional specific logger name, if None sets root logger
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()
    
    logger.setLevel(numeric_level)
    
    # Also update console handler if changing root logger
    if not logger_name:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                handler.setLevel(max(numeric_level, logging.WARNING))  # Console stays at WARNING minimum


def add_file_handler(logger_name: str, log_file: Path, level: int = logging.DEBUG):
    """
    Add an additional file handler to a specific logger with daily rotation.
    
    Args:
        logger_name: Name of the logger
        log_file: Path to the log file
        level: Logging level for this handler
    """
    logger = logging.getLogger(logger_name)
    
    # Create handler with daily rotation
    handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding='utf-8'
    )
    
    # Set formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    handler.suffix = "%Y%m%d"  # Add date suffix to rotated files
    
    # Add handler
    logger.addHandler(handler)


# Initialize logging on module import if running as main program
if __name__ != "__main__" and os.environ.get('CIVITAI_AUTO_LOGGING', 'true').lower() == 'true':
    # Auto-initialize logging when module is imported
    setup_logging()