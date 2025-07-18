"""Cross-platform utilities."""

import os
import platform
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple

from platformdirs import user_data_dir, user_config_dir, user_cache_dir


def get_platform_info() -> dict:
    """Get platform information."""
    return {
        'system': platform.system(),
        'version': platform.version(),
        'machine': platform.machine(),
        'python_version': platform.python_version()
    }


def get_app_dirs() -> dict:
    """Get platform-specific application directories."""
    app_name = "civitai-downloader"
    return {
        'data': Path(user_data_dir(app_name)),
        'config': Path(user_config_dir(app_name)),
        'cache': Path(user_cache_dir(app_name))
    }


def get_app_data_dir() -> Path:
    """Get application data directory."""
    return get_app_dirs()['data']


def ensure_app_dirs() -> None:
    """Ensure application directories exist."""
    dirs = get_app_dirs()
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility."""
    # Remove invalid characters
    if platform.system() == 'Windows':
        # Windows reserved characters
        invalid_chars = r'<>:"|?*'
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
    else:
        # Unix-like systems
        invalid_chars = '\0'
        reserved_names = set()
    
    # Replace invalid characters
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Handle reserved names
    name_without_ext = filename.split('.')[0].upper()
    if name_without_ext in reserved_names:
        filename = f'_{filename}'
    
    # Limit length (255 for most systems, but leave room for path)
    max_length = 200
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    return filename


def get_disk_usage(path: Path) -> Tuple[int, int, int]:
    """Get disk usage statistics (total, used, free) in bytes."""
    stat = shutil.disk_usage(path)
    return stat.total, stat.used, stat.free


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def format_time(seconds: float) -> str:
    """Format seconds to human readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def parse_size(size_str: str) -> Optional[int]:
    """Parse human readable size string to bytes."""
    size_str = size_str.strip().upper()
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', size_str)
    
    if not match:
        return None
    
    value, unit = match.groups()
    value = float(value)
    
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }
    
    multiplier = units.get(unit, 1)
    return int(value * multiplier)


def get_terminal_size() -> Tuple[int, int]:
    """Get terminal size (columns, rows)."""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except:
        # Fallback for non-terminal environments
        return 80, 24


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def normalize_path(path: Path) -> Path:
    """Normalize path for cross-platform compatibility."""
    # Resolve to absolute path
    path = path.resolve()
    
    # Handle Windows long path prefix
    if platform.system() == 'Windows':
        path_str = str(path)
        if not path_str.startswith('\\\\?\\') and len(path_str) > 260:
            path = Path(f'\\\\?\\{path_str}')
    
    return path