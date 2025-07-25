"""
SystemConfig - Comprehensive configuration management system.

This module provides unified configuration management with YAML file support,
environment variable overrides, type conversion, validation, and secure handling
of sensitive data.
"""

import contextlib
import logging
import os
import yaml
import re
from typing import Dict, Any, Optional, Union
from pathlib import Path
from urllib.parse import urlparse

try:
    from .env_loader import ensure_env_loaded
except ImportError:
    # Handle relative import issues
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from env_loader import ensure_env_loaded


class SystemConfig:
    """
    Comprehensive system configuration management.
    
    This class provides centralized configuration management with support for:
    - YAML configuration files
    - Environment variable overrides with automatic type conversion
    - Nested key access using dot notation
    - Configuration validation with sensible defaults
    - Secure sensitive data masking for logging/debugging
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize system configuration.
        
        Args:
            config_file: Path to YAML configuration file (optional)
        """
        self._config_data = {}
        self._defaults = self._setup_defaults()
        
        # Ensure .env files are loaded first
        ensure_env_loaded()
        
        # Load configuration from file if provided
        if config_file and Path(config_file).exists():
            self._load_yaml_config(config_file)
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        # Merge with defaults
        self._merge_defaults()
    
    def _setup_defaults(self) -> Dict[str, Any]:
        """Setup default configuration values."""
        return {
            'api': {
                'base_url': 'https://civitai.com/api/v1',
                'timeout': 30,
                'max_retries': 3.0,
                'api_key': None  # Required, no default
            },
            'download': {
                'dir': 'downloads',
                'temp_dir': 'downloads/temp',
                'concurrent_downloads': 1,
                'chunk_size': 8192,
                'max_file_size_per_download_gb': 10.0,
                'organize_by_type': True,
                'organize_by_creator': False
            },
            'reports': {
                'dir': 'reports',
                'default_format': 'json'
            },
            'security': {
                'verify_ssl': True,
                'enable_scan': True,
                'quarantine_dir': 'quarantine'
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/civitai.log'
            },
            'database': {
                'path': 'data/civitai.db'
            }
        }
    
    def _load_yaml_config(self, config_file: str) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f) or {}
                self._config_data = yaml_data
        except (yaml.YAMLError, IOError) as e:
            # Log config file errors for debugging, but don't fail
            logging.warning(f"Failed to load config file {config_file}: {e}")
            logging.info("Using default configuration with environment variable overrides")
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        env_mappings = {
            # API Configuration
            'CIVITAI_API_KEY': 'api.api_key',
            'CIVITAI_BASE_URL': 'api.base_url',
            'CIVITAI_TIMEOUT': 'api.timeout',
            'CIVITAI_MAX_RETRIES': 'api.max_retries',
            
            # Download Configuration
            'CIVITAI_DOWNLOAD_DIR': 'download.dir',
            'CIVITAI_TEMP_DIR': 'download.temp_dir',
            'CIVITAI_CONCURRENT_DOWNLOADS': 'download.concurrent_downloads',
            'CIVITAI_CHUNK_SIZE': 'download.chunk_size',
            'CIVITAI_MAX_FILE_SIZE_PER_DOWNLOAD_GB': 'download.max_file_size_per_download_gb',
            'CIVITAI_ORGANIZE_BY_TYPE': 'download.organize_by_type',
            'CIVITAI_ORGANIZE_BY_CREATOR': 'download.organize_by_creator',
            
            # Reports Configuration
            'CIVITAI_REPORTS_DIR': 'reports.dir',
            'CIVITAI_DEFAULT_OUTPUT_FORMAT': 'reports.default_format',
            
            # Security Configuration
            'CIVITAI_VERIFY_SSL': 'security.verify_ssl',
            'CIVITAI_ENABLE_SECURITY_SCAN': 'security.enable_scan',
            'CIVITAI_QUARANTINE_DIR': 'security.quarantine_dir',
            
            # Logging Configuration
            'CIVITAI_LOG_LEVEL': 'logging.level',
            'CIVITAI_LOG_FILE': 'logging.file',
            
            # Database Configuration
            'CIVITAI_DATABASE_PATH': 'database.path'
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # Convert types based on expected type
                converted_value = self._convert_env_value(config_path, value)
                self._set_nested_value(config_path, converted_value)
    
    def _convert_env_value(self, config_path: str, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        boolean_paths = [
            'security.verify_ssl', 'security.enable_scan',
            'download.organize_by_type', 'download.organize_by_creator'
        ]
        if config_path in boolean_paths:
            return value.lower() in ('true', '1', 'yes', 'on')
        
        # Integer conversion
        integer_paths = [
            'api.timeout', 'download.concurrent_downloads', 'download.chunk_size'
        ]
        if config_path in integer_paths:
            try:
                return int(value)
            except ValueError:
                return value  # Return as string if conversion fails
        
        # Float conversion
        float_paths = [
            'api.max_retries', 'download.max_file_size_per_download_gb'
        ]
        if config_path in float_paths:
            try:
                return float(value)
            except ValueError:
                return value  # Return as string if conversion fails
        
        # String (default)
        return value
    
    def _merge_defaults(self) -> None:
        """Merge configuration with defaults."""
        self._config_data = self._deep_merge(self._defaults, self._config_data)
    
    def _deep_merge(self, default_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override_dict taking precedence."""
        result = default_dict.copy()
        
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _set_nested_value(self, key_path: str, value: Any) -> None:
        """Set value using dot notation path."""
        keys = key_path.split('.')
        current = self._config_data
        
        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the final value
        current[keys[-1]] = value
    
    def _get_nested_value(self, key_path: str, default: Any = None) -> Any:
        """Get value using dot notation path."""
        keys = key_path.split('.')
        current = self._config_data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to configuration value
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._get_nested_value(key_path, default)
    
    def validate(self) -> None:
        """
        Validate configuration for required fields and constraints.
        
        Raises:
            ValueError: If validation fails
        """
        # Check required API key
        api_key = self.get('api.api_key')
        if not api_key:
            raise ValueError("API key is required")
        
        # Validate API timeout
        timeout = self.get('api.timeout')
        if timeout is not None and timeout < 0:
            raise ValueError("API timeout must be positive")
        
        # Validate base URL format
        base_url = self.get('api.base_url')
        if base_url:
            parsed = urlparse(base_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Base URL must be a valid URL")
        
        # Validate concurrent downloads limit
        concurrent = self.get('download.concurrent_downloads')
        if concurrent is not None and (concurrent < 1 or concurrent > 50):
            raise ValueError("Concurrent downloads must be between 1 and 50")
    
    def to_dict(self, mask_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Args:
            mask_sensitive: Whether to mask sensitive values
            
        Returns:
            Configuration as dictionary
        """
        if not mask_sensitive:
            return self._config_data.copy()
        
        # Create masked copy
        masked_config = self._deep_copy_and_mask(self._config_data)
        return masked_config
    
    def _deep_copy_and_mask(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deep copy dictionary and mask sensitive values."""
        result = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._deep_copy_and_mask(value)
            elif self._is_sensitive_key(key):
                if value:
                    result[key] = f"***{str(value)[-4:]}" if len(str(value)) > 4 else "***"
                else:
                    result[key] = "REDACTED"
            else:
                result[key] = value
        
        return result
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a key contains sensitive data."""
        sensitive_patterns = ['key', 'token', 'password', 'secret', 'auth']
        return any(pattern in key.lower() for pattern in sensitive_patterns)